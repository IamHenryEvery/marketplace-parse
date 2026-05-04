"""Parsing endpoints: trigger, status polling, analysis aggregates."""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from marketplace_parse.api.deps import (
    CurrentUser,
    get_owned_product_or_404,
    latest_analyses,
    parse_progress,
)
from marketplace_parse.api.schemas import (
    AnalysisItem,
    MarketplaceOut,
    ParseRunListItem,
    ParseTriggerOut,
    ProgressOut,
    RunAnalysisOut,
)
from marketplace_parse.db.enums import ParseStatus, SentimentLabel
from marketplace_parse.db.models import (
    Marketplace,
    ParseRun,
    Product,
    ProductURL,
    Review,
    User,
)
from marketplace_parse.db.session import async_session_maker
from marketplace_parse.mq import publish_parse_task
from marketplace_parse.parsers.runner import enqueue_parse


router = APIRouter()


@router.post(
    "/products/{product_id}/parse",
    response_model=ParseTriggerOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_parse(product_id: int, user: User = CurrentUser) -> ParseTriggerOut:
    async with async_session_maker() as session:
        product = await get_owned_product_or_404(session, product_id, user.user_id)
        url_ids = [u.url_id for u in product.urls]

    if not url_ids:
        raise HTTPException(status_code=400, detail="У товара нет ссылок")

    run_ids: list[int] = []
    for url_id in url_ids:
        run_id: int | None = None
        try:
            run_id, slug = await enqueue_parse(url_id)
            await publish_parse_task(run_id, slug)
            run_ids.append(run_id)
        except Exception as exc:
            if run_id is not None:
                async with async_session_maker() as session:
                    run = await session.get(ParseRun, run_id)
                    if run is not None and run.status == ParseStatus.pending:
                        run.status = ParseStatus.failed
                        run.error_message = f"enqueue failed: {exc!r}"
                        run.finished_at = datetime.now(timezone.utc)
                        await session.commit()

    return ParseTriggerOut(run_ids=run_ids)


@router.get("/products/{product_id}/parse/status", response_model=ProgressOut)
async def get_parse_status(product_id: int, user: User = CurrentUser) -> ProgressOut:
    async with async_session_maker() as session:
        await get_owned_product_or_404(session, product_id, user.user_id)
        return await parse_progress(session, product_id)


@router.get("/products/{product_id}/analysis", response_model=list[AnalysisItem])
async def get_analysis(product_id: int, user: User = CurrentUser) -> list[AnalysisItem]:
    async with async_session_maker() as session:
        await get_owned_product_or_404(session, product_id, user.user_id)
        return await latest_analyses(session, product_id)


@router.get("/parse-runs", response_model=list[ParseRunListItem])
async def list_user_parse_runs(user: User = CurrentUser) -> list[ParseRunListItem]:
    """All parse_runs across the current user's products, newest first."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(ParseRun, ProductURL, Product, Marketplace)
            .join(ProductURL, ProductURL.url_id == ParseRun.url_id)
            .join(Product, Product.product_id == ProductURL.product_id)
            .join(Marketplace, Marketplace.marketplace_id == ProductURL.marketplace_id)
            .where(Product.user_id == user.user_id)
            .order_by(
                # COALESCE so pending runs (no started_at yet) sort by their created_at.
                func.coalesce(ParseRun.started_at, ParseRun.created_at).desc()
            )
        )
        items: list[ParseRunListItem] = []
        for run, url, product, mp in result.all():
            items.append(
                ParseRunListItem(
                    run_id=run.run_id,
                    product_id=product.product_id,
                    product_name=product.name,
                    url=url.url,
                    marketplace=MarketplaceOut.model_validate(mp),
                    status=run.status.value,
                    started_at=run.started_at,
                    finished_at=run.finished_at,
                    created_at=run.created_at,
                    reviews_collected=run.reviews_collected,
                    error_message=run.error_message,
                )
            )
        return items


@router.get("/parse-runs/{run_id}/analysis", response_model=RunAnalysisOut)
async def get_run_analysis(run_id: int, user: User = CurrentUser) -> RunAnalysisOut:
    """Sentiment breakdown of reviews collected by a single parse run."""
    async with async_session_maker() as session:
        row = (
            await session.execute(
                select(ParseRun, Product, Marketplace)
                .join(ProductURL, ProductURL.url_id == ParseRun.url_id)
                .join(Product, Product.product_id == ProductURL.product_id)
                .join(Marketplace, Marketplace.marketplace_id == ProductURL.marketplace_id)
                .where(ParseRun.run_id == run_id, Product.user_id == user.user_id)
            )
        ).first()
        if row is None:
            raise HTTPException(status_code=404)
        run, product, mp = row

        counts_q = await session.execute(
            select(Review.sentiment_label, func.count(Review.review_id))
            .where(Review.run_id == run_id)
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
            select(func.avg(Review.sentiment_score)).where(Review.run_id == run_id)
        )

        return RunAnalysisOut(
            run_id=run_id,
            product_name=product.name,
            marketplace=MarketplaceOut.model_validate(mp),
            status=run.status.value,
            total_reviews=pos + neg + neu,
            positive_count=pos,
            negative_count=neg,
            neutral_count=neu,
            avg_sentiment=float(avg or 0.0),
        )
