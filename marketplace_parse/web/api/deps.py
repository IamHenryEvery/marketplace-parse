from dataclasses import dataclass
from pathlib import Path

from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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


TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@dataclass
class ProductCard:
    product: Product
    marketplaces: list[Marketplace]




async def get_current_user(request: Request) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    async with async_session_maker() as session:
        return await session.get(User, user_id)


def require_user_or_redirect(user: User | None) -> RedirectResponse | None:
    if user is None:
        return RedirectResponse("/login", status_code=303)
    return None



async def load_user_cards(session: AsyncSession, user_id: int) -> list[ProductCard]:
    result = await session.execute(
        select(Product)
        .where(Product.user_id == user_id)
        .options(selectinload(Product.urls).selectinload(ProductURL.marketplace))
        .order_by(Product.created_at.desc())
    )
    cards: list[ProductCard] = []
    for product in result.scalars():
        seen: set[int] = set()
        marketplaces: list[Marketplace] = []
        for url in product.urls:
            mp = url.marketplace
            if mp.marketplace_id not in seen:
                seen.add(mp.marketplace_id)
                marketplaces.append(mp)
        cards.append(ProductCard(product=product, marketplaces=marketplaces))
    return cards


async def load_marketplaces(session: AsyncSession) -> list[Marketplace]:
    result = await session.execute(
        select(Marketplace)
        .where(Marketplace.is_active.is_(True))
        .order_by(Marketplace.marketplace_id)
    )
    return list(result.scalars().all())


async def load_owned_product(
    session: AsyncSession, product_id: int, user_id: int
) -> Product | None:
    return await session.scalar(
        select(Product)
        .where(Product.product_id == product_id, Product.user_id == user_id)
        .options(selectinload(Product.urls).selectinload(ProductURL.marketplace))
    )



async def latest_analyses(
    session: AsyncSession, product_id: int
) -> list[tuple[Marketplace, AnalysisResult | None]]:
    mps_q = await session.execute(
        select(Marketplace)
        .join(ProductURL, ProductURL.marketplace_id == Marketplace.marketplace_id)
        .where(ProductURL.product_id == product_id)
        .distinct()
        .order_by(Marketplace.marketplace_id)
    )
    out: list[tuple[Marketplace, AnalysisResult | None]] = []
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
        out.append((mp, latest))
    return out


async def parse_progress(session: AsyncSession, product_id: int) -> dict:
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
    total = pending + running + completed + failed

    return {
        "urls": urls,
        "latest_by_url": latest_by_url,
        "pending": pending,
        "running": running,
        "completed": completed,
        "failed": failed,
        "in_flight": pending + running,
        "total": total,
    }
