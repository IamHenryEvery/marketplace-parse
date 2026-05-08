import csv
import io
from datetime import date, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from marketplace_parse.api.deps import CurrentUser
from marketplace_parse.api.schemas import FeedReviewItem, MarketplaceOut
from marketplace_parse.db.enums import SentimentLabel, UserRole
from marketplace_parse.db.models import Marketplace, Product, ProductURL, Review, User
from marketplace_parse.db.session import async_session_maker


router = APIRouter()

SentimentParam = Literal["positive", "neutral", "negative"]


def _ensure_analyst_or_admin(user: User) -> None:
    if user.role not in (UserRole.analyst, UserRole.admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для аналитиков и администраторов",
        )


def _build_filtered_select(
    marketplace: str | None,
    sentiment: SentimentParam | None,
    date_from: date | None,
    date_to: date | None,
):
    """Cross-user reviews query with optional filters. Returns (Review, Product, Marketplace) rows."""
    stmt = (
        select(Review, Product, Marketplace)
        .join(ProductURL, ProductURL.url_id == Review.url_id)
        .join(Product, Product.product_id == ProductURL.product_id)
        .join(Marketplace, Marketplace.marketplace_id == ProductURL.marketplace_id)
        .order_by(Review.created_at.desc())
    )
    if marketplace:
        stmt = stmt.where(Marketplace.slug == marketplace)
    if sentiment is not None:
        stmt = stmt.where(Review.sentiment_label == SentimentLabel(sentiment))
    if date_from is not None:
        stmt = stmt.where(Review.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to is not None:
        # `to` is inclusive at day-level — extend to start of next day
        stmt = stmt.where(
            Review.created_at < datetime.combine(date_to + timedelta(days=1), datetime.min.time())
        )
    return stmt


@router.get("/analytics/feed", response_model=list[FeedReviewItem])
async def feed(
    marketplace: str | None = Query(None, description="marketplace slug"),
    sentiment: SentimentParam | None = Query(None),
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = CurrentUser,
) -> list[FeedReviewItem]:
    _ensure_analyst_or_admin(user)
    stmt = _build_filtered_select(marketplace, sentiment, date_from, date_to)
    stmt = stmt.limit(limit).offset(offset)

    async with async_session_maker() as session:
        result = await session.execute(stmt)
        items: list[FeedReviewItem] = []
        for review, product, mp in result.all():
            items.append(
                FeedReviewItem(
                    review_id=review.review_id,
                    review_text=review.review_text,
                    review_date=(
                        datetime.combine(review.review_date, datetime.min.time())
                        if review.review_date is not None
                        else None
                    ),
                    sentiment_label=(
                        review.sentiment_label.value if review.sentiment_label else None
                    ),
                    sentiment_score=review.sentiment_score,
                    created_at=review.created_at,
                    marketplace=MarketplaceOut.model_validate(mp),
                    product_name=product.name,
                )
            )
        return items


_CSV_COLUMNS = [
    "review_id",
    "marketplace_slug",
    "marketplace_name",
    "product_name",
    "review_date",
    "sentiment_label",
    "sentiment_score",
    "created_at",
    "review_text",
]


async def _csv_iterator(session: AsyncSession, stmt) -> "io.StringIO":  # type: ignore[name-defined]
    """Stream rows from DB and yield CSV chunks (header first, then row by row)."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(_CSV_COLUMNS)
    yield buf.getvalue()
    buf.seek(0)
    buf.truncate(0)

    result = await session.stream(stmt)
    async for review, product, mp in result:
        writer.writerow(
            [
                review.review_id,
                mp.slug,
                mp.display_name,
                product.name,
                review.review_date.isoformat() if review.review_date else "",
                review.sentiment_label.value if review.sentiment_label else "",
                f"{review.sentiment_score:.4f}" if review.sentiment_score is not None else "",
                review.created_at.isoformat(),
                review.review_text.replace("\r\n", " ").replace("\n", " "),
            ]
        )
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)


@router.get("/analytics/export.csv")
async def export_csv(
    marketplace: str | None = Query(None),
    sentiment: SentimentParam | None = Query(None),
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    user: User = CurrentUser,
) -> StreamingResponse:
    _ensure_analyst_or_admin(user)
    stmt = _build_filtered_select(marketplace, sentiment, date_from, date_to)

    parts = ["reviews"]
    if marketplace:
        parts.append(marketplace)
    if date_from:
        parts.append(date_from.isoformat())
    if date_to:
        parts.append(date_to.isoformat())
    filename = "_".join(parts) + ".csv"

    session = async_session_maker()

    async def streamer():
        async with session as s:
            async for chunk in _csv_iterator(s, stmt):
                yield chunk

    return StreamingResponse(
        streamer(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )
