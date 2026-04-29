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
        product_id = product_url.product_id
        marketplace_id = product_url.marketplace_id

        await session.commit()

    async with async_session_maker() as session:
        await _record_analysis(session, product_id, marketplace_id)
        await session.commit()

    return len(reviews)


async def _record_analysis(session: AsyncSession, product_id: int, marketplace_id: int) -> None:
    """Insert a fresh analysis_result row aggregating reviews across all URLs
    of (product_id, marketplace_id). History rows are kept; we don't update in place.
    """
    url_subq = (
        select(ProductURL.url_id)
        .where(ProductURL.product_id == product_id)
        .where(ProductURL.marketplace_id == marketplace_id)
        .scalar_subquery()
    )
    counts_q = await session.execute(
        select(Review.sentiment_label, func.count(Review.review_id))
        .where(Review.url_id.in_(url_subq))
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
        select(func.avg(Review.sentiment_score)).where(Review.url_id.in_(url_subq))
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
