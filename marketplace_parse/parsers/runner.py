import asyncio
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from marketplace_parse.db.enums import ParseStatus, SentimentLabel
from marketplace_parse.db.models import (
    AnalysisResult,
    Marketplace,
    ParseRun,
    ProductURL,
    Review,
)
from marketplace_parse.db.session import async_session_maker
from marketplace_parse.parsers import megamarket, wildberries, yandex_market
from marketplace_parse.sentiment.analyzer import analyze as analyze_sentiment


PARSERS = {
    "yandex_market": yandex_market.parse,
    "wildberries": wildberries.parse,
    "megamarket": megamarket.parse,
}


async def enqueue_parse(url_id: int) -> tuple[int, str]:
    async with async_session_maker() as session:
        product_url = await session.get(ProductURL, url_id)
        if product_url is None:
            raise ValueError(f"product_url id={url_id} not found")
        marketplace = await session.get(Marketplace, product_url.marketplace_id)
        if marketplace is None:
            raise ValueError(f"marketplace id={product_url.marketplace_id} not found")
        if marketplace.slug not in PARSERS:
            raise ValueError(f"no parser registered for marketplace slug={marketplace.slug!r}")
        run = ParseRun(url_id=url_id, status=ParseStatus.pending)
        session.add(run)
        await session.commit()
        await session.refresh(run)
        return run.run_id, marketplace.slug


async def execute_parse(run_id: int) -> int:

    async with async_session_maker() as session:
        run = await session.get(ParseRun, run_id)
        if run is None:
            raise ValueError(f"parse_run id={run_id} not found")
        if run.status != ParseStatus.pending:
            return run.reviews_collected

        product_url = await session.get(ProductURL, run.url_id)
        if product_url is None:
            run.status = ParseStatus.failed
            run.finished_at = datetime.now(timezone.utc)
            run.error_message = f"product_url id={run.url_id} not found"
            await session.commit()
            raise ValueError(run.error_message)

        marketplace = await session.get(Marketplace, product_url.marketplace_id)
        parser = PARSERS.get(marketplace.slug) if marketplace else None
        if parser is None:
            run.status = ParseStatus.failed
            run.finished_at = datetime.now(timezone.utc)
            run.error_message = f"no parser for marketplace slug={marketplace.slug if marketplace else None!r}"
            await session.commit()
            raise ValueError(run.error_message)

        run.status = ParseStatus.running
        run.started_at = datetime.now(timezone.utc)
        url = product_url.url
        url_id = product_url.url_id
        await session.commit()

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
        product_id = product_url.product_id
        marketplace_id = product_url.marketplace_id

        await session.commit()

    async with async_session_maker() as session:
        await _record_analysis(session, product_id, marketplace_id)
        await session.commit()

    return len(reviews)


async def run_parse(url_id: int) -> int:

    run_id, _ = await enqueue_parse(url_id)
    return await execute_parse(run_id)


async def _record_analysis(session: AsyncSession, product_id: int, marketplace_id: int) -> None:
    url_ids_subq = (
        select(ProductURL.url_id)
        .where(ProductURL.product_id == product_id)
        .where(ProductURL.marketplace_id == marketplace_id)
    )
    latest_run_ids = (
        select(func.max(ParseRun.run_id))
        .where(ParseRun.url_id.in_(url_ids_subq))
        .group_by(ParseRun.url_id)
    )

    counts_q = await session.execute(
        select(Review.sentiment_label, func.count(Review.review_id))
        .where(Review.run_id.in_(latest_run_ids))
        .group_by(Review.sentiment_label)
    )
    pos = neg = neu = 0
    for label, count in counts_q.all():
        if label is SentimentLabel.positive:
            pos = count
        elif label is SentimentLabel.negative:
            neg = count
        elif label is SentimentLabel.neutral:
            neu = count

    avg = await session.scalar(
        select(func.avg(Review.sentiment_score)).where(Review.run_id.in_(latest_run_ids))
    )
    session.add(
        AnalysisResult(
            product_id=product_id,
            marketplace_id=marketplace_id,
            total_reviews=pos + neg + neu,
            positive_count=pos,
            negative_count=neg,
            neutral_count=neu,
            avg_sentiment=float(avg or 0.0),
        )
    )
