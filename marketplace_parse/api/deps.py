"""Dependencies shared across JSON routers: auth + DB loaders."""
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from marketplace_parse.api.schemas import (
    AnalysisItem,
    AnalysisLatest,
    LastRunInfo,
    MarketplaceOut,
    ParseRunSummary,
    ProductOut,
    ProductURLOut,
    ProgressOut,
)
from marketplace_parse.db.enums import ParseStatus
from marketplace_parse.db.models import (
    AnalysisResult,
    Marketplace,
    ParseRun,
    Product,
    ProductURL,
    User,
)
from marketplace_parse.db.session import async_session_maker


# ---------- auth ----------

async def current_user(request: Request) -> User:
    """Auth-required dependency. Raises 401 if no session."""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Не авторизован")
    async with async_session_maker() as session:
        user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Не авторизован")
    return user


CurrentUser = Depends(current_user)


# ---------- product loaders + serializers ----------

def _product_to_out(product: Product) -> ProductOut:
    return ProductOut(
        product_id=product.product_id,
        name=product.name,
        created_at=product.created_at,
        urls=[
            ProductURLOut(
                url_id=u.url_id,
                url=u.url,
                marketplace=MarketplaceOut.model_validate(u.marketplace),
            )
            for u in product.urls
        ],
    )


async def load_user_products(session: AsyncSession, user_id: int) -> list[ProductOut]:
    result = await session.execute(
        select(Product)
        .where(Product.user_id == user_id)
        .options(selectinload(Product.urls).selectinload(ProductURL.marketplace))
        .order_by(Product.created_at.desc())
    )
    return [_product_to_out(p) for p in result.scalars()]


async def load_owned_product(
    session: AsyncSession, product_id: int, user_id: int
) -> Product | None:
    return await session.scalar(
        select(Product)
        .where(Product.product_id == product_id, Product.user_id == user_id)
        .options(selectinload(Product.urls).selectinload(ProductURL.marketplace))
    )


async def get_owned_product_or_404(
    session: AsyncSession, product_id: int, user_id: int
) -> Product:
    product = await load_owned_product(session, product_id, user_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return product


# ---------- parsing helpers ----------

async def parse_progress(session: AsyncSession, product_id: int) -> ProgressOut:
    """Latest parse_run per URL of this product + counts by status."""
    urls_q = await session.execute(
        select(ProductURL)
        .where(ProductURL.product_id == product_id)
        .options(selectinload(ProductURL.marketplace))
        .order_by(ProductURL.url_id)
    )
    urls = list(urls_q.scalars())

    latest_by_url: dict[int, ParseRun | None] = {}
    for url in urls:
        latest = await session.scalar(
            select(ParseRun)
            .where(ParseRun.url_id == url.url_id)
            .order_by(ParseRun.run_id.desc())
            .limit(1)
        )
        latest_by_url[url.url_id] = latest

    pending = sum(1 for r in latest_by_url.values() if r is not None and r.status == ParseStatus.pending)
    running = sum(1 for r in latest_by_url.values() if r is not None and r.status == ParseStatus.running)
    completed = sum(1 for r in latest_by_url.values() if r is not None and r.status == ParseStatus.completed)
    failed = sum(1 for r in latest_by_url.values() if r is not None and r.status == ParseStatus.failed)

    runs: list[ParseRunSummary] = []
    for url in urls:
        run = latest_by_url[url.url_id]
        last = (
            LastRunInfo(
                status=run.status.value,
                started_at=run.started_at,
                finished_at=run.finished_at,
                reviews_collected=run.reviews_collected,
                error_message=run.error_message,
            )
            if run is not None
            else None
        )
        runs.append(
            ParseRunSummary(
                url_id=url.url_id,
                url=url.url,
                marketplace=MarketplaceOut.model_validate(url.marketplace),
                last_run=last,
            )
        )

    return ProgressOut(
        pending=pending,
        running=running,
        completed=completed,
        failed=failed,
        in_flight=pending + running,
        total=pending + running + completed + failed,
        runs=runs,
    )


async def latest_analyses(session: AsyncSession, product_id: int) -> list[AnalysisItem]:
    mps_q = await session.execute(
        select(Marketplace)
        .join(ProductURL, ProductURL.marketplace_id == Marketplace.marketplace_id)
        .where(ProductURL.product_id == product_id)
        .distinct()
        .order_by(Marketplace.marketplace_id)
    )
    out: list[AnalysisItem] = []
    for mp in mps_q.scalars():
        latest = await session.scalar(
            select(AnalysisResult)
            .where(
                AnalysisResult.product_id == product_id,
                AnalysisResult.marketplace_id == mp.marketplace_id,
            )
            .order_by(AnalysisResult.calculated_at.desc())
            .limit(1)
        )
        out.append(
            AnalysisItem(
                marketplace=MarketplaceOut.model_validate(mp),
                latest=(
                    AnalysisLatest(
                        total_reviews=latest.total_reviews,
                        positive_count=latest.positive_count,
                        negative_count=latest.negative_count,
                        neutral_count=latest.neutral_count,
                        avg_sentiment=latest.avg_sentiment,
                        calculated_at=latest.calculated_at,
                    )
                    if latest is not None
                    else None
                ),
            )
        )
    return out
