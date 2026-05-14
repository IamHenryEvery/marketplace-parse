import argparse
import asyncio
import json
import logging
from contextlib import suppress

import aio_pika

from marketplace_parse.core.config import settings
from marketplace_parse.mq import queue_name_for
from marketplace_parse.parsers.runner import VALID_SLUGS, execute_parse


log = logging.getLogger("marketplace_parse.worker")


async def run_worker(marketplace_slug: str) -> None:
    if marketplace_slug not in VALID_SLUGS:
        raise SystemExit(
            f"неизвестный slug маркетплейса {marketplace_slug!r}; "
            f"известные: {sorted(VALID_SLUGS)}"
        )
    qname = queue_name_for(marketplace_slug)
    log.info("подключение к %s, очередь %s", settings.rabbitmq_host, qname)
    connection = await aio_pika.connect_robust(settings.rabbitmq_dsn)
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)
        queue = await channel.declare_queue(qname, durable=True)
        log.info("ожидание сообщений в %s (Ctrl-C для остановки)", qname)
        async with queue.iterator() as it:
            async for message in it:
                async with message.process(requeue=False, ignore_processed=True):
                    try:
                        payload = json.loads(message.body)
                        run_id = int(payload["run_id"])
                    except (ValueError, KeyError, TypeError) as exc:
                        log.error("некорректное тело сообщения=%r (%s); отбрасываем", message.body, exc)
                        continue
                    log.info("обработка run_id=%s", run_id)
                    try:
                        count = await execute_parse(run_id)
                        log.info("run_id=%s выполнен, отзывов: %d", run_id, count)
                    except Exception as exc:
                        log.exception("run_id=%s завершился с ошибкой: %s", run_id, exc)


def main() -> None:
    p = argparse.ArgumentParser(description="Marketplace parse worker.")
    p.add_argument(
        "--marketplace",
        required=True,
        help=f"marketplace slug; known: {sorted(VALID_SLUGS)}",
    )
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args()

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    with suppress(KeyboardInterrupt):
        asyncio.run(run_worker(args.marketplace))


if __name__ == "__main__":
    main()
