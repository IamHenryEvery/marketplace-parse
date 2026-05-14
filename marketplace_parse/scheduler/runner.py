import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from marketplace_parse.db.models import Product, ProductURL, User
from marketplace_parse.db.session import async_session_maker
from marketplace_parse.mq import publish_parse_task
from marketplace_parse.parsers.runner import enqueue_parse


log = logging.getLogger("marketplace_parse.scheduler")


CRON_HOUR = 3
CRON_MINUTE = 0
TIMEZONE = "UTC"


async def daily_parse_all_users() -> None:
    async with async_session_maker() as session:
        users = list(
            (
                await session.execute(
                    select(User).where(User.scheduler_enabled.is_(True))
                )
            ).scalars()
        )

    log.info("daily run: %d user(s) opted in", len(users))

    for user in users:
        async with async_session_maker() as session:
            url_ids = list(
                (
                    await session.execute(
                        select(ProductURL.url_id)
                        .join(Product, Product.product_id == ProductURL.product_id)
                        .where(
                            Product.user_id == user.user_id,
                            ProductURL.is_active.is_(True),
                        )
                    )
                ).scalars()
            )

        log.info("user_id=%s: enqueuing %d url(s)", user.user_id, len(url_ids))
        for url_id in url_ids:
            try:
                run_id, slug = await enqueue_parse(url_id)
                await publish_parse_task(run_id, slug)
            except Exception:
                log.exception("user_id=%s url_id=%s: enqueue failed", user.user_id, url_id)


async def main() -> None:
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(
        daily_parse_all_users,
        CronTrigger(hour=CRON_HOUR, minute=CRON_MINUTE, timezone=TIMEZONE),
        id="daily_parse",
        replace_existing=True,
    )
    scheduler.start()
    log.info(
        "Планировщик запущен; Ежедневный прогон стартует в  %02d:%02d %s",
        CRON_HOUR, CRON_MINUTE, TIMEZONE,
    )
    try:
        await asyncio.Event().wait()
    finally:
        scheduler.shutdown()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
