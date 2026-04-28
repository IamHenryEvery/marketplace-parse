import asyncio
from datetime import datetime, timezone

from marketplace_parse.db.enums import ParseStatus, SentimentLabel
from marketplace_parse.db.models import Marketplace, ParseRun, ProductURL, Review
from marketplace_parse.db.session import async_session_maker
from marketplace_parse.parsers import wildberries, yandex_market
from marketplace_parse.sentiment.analyzer import analyze as analyze_sentiment


PARSERS = {
    "yandex_market": yandex_market.parse,
    "wildberries": wildberries.parse,
}


async def run_parse(url_id: int) -> int:
    async with async_session_maker() as session:
        product_url = await session.get(ProductURL, url_id)
        if product_url is None:
            raise ValueError(f"product_url id={url_id} not found")

        marketplace = await session.get(Marketplace, product_url.marketplace_id)
        parser = PARSERS.get(marketplace.slug)
        if parser is None:
            raise ValueError(f"no parser registered for marketplace slug={marketplace.slug!r}")

        url = product_url.url
        run = ParseRun(
            url_id=url_id,
            status=ParseStatus.running,
            started_at=datetime.now(timezone.utc),
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)
        run_id = run.run_id

    try:
        reviews = await asyncio.to_thread(parser, url)
    except Exception as exc:
        async with async_session_maker() as session:
            run = await session.get(ParseRun, run_id)
            run.status = ParseStatus.failed
            run.finished_at = datetime.now(timezone.utc)
            run.error_message = repr(exc)
            await session.commit()
        raise

    sentiments: list[tuple[SentimentLabel, float] | None]
    if reviews:
        try:
            sentiments = await asyncio.to_thread(
                analyze_sentiment, [r.review_text for r in reviews]
            )
        except Exception:
            sentiments = [None] * len(reviews)
    else:
        sentiments = []

    async with async_session_maker() as session:
        finished = datetime.now(timezone.utc)
        for parsed, sent in zip(reviews, sentiments):
            label = sent[0] if sent else None
            score = sent[1] if sent else None
            session.add(
                Review(
                    url_id=url_id,
                    run_id=run_id,
                    review_text=parsed.review_text,
                    review_date=parsed.review_date,
                    sentiment_label=label,
                    sentiment_score=score,
                )
            )
        run = await session.get(ParseRun, run_id)
        run.status = ParseStatus.completed
        run.finished_at = finished
        run.reviews_collected = len(reviews)

        product_url = await session.get(ProductURL, url_id)
        product_url.last_parsed_at = finished

        await session.commit()

    return len(reviews)
