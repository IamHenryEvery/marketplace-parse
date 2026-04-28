from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from marketplace_parse.db.enums import SentimentLabel, UserRole
from marketplace_parse.db.models import (
    Marketplace,
    ParseRun,
    Product,
    ProductURL,
    Review,
    User,
)
from marketplace_parse.db.session import async_session_maker
from marketplace_parse.parsers.runner import run_parse


@dataclass
class UrlState:
    last_run: ParseRun | None
    review_count: int
    pos: int
    neg: int
    neu: int
    no_sentiment: int


TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

app = FastAPI(title="marketplace-parse (dev)")


async def _default_user(session: AsyncSession) -> User:
    user = await session.scalar(
        select(User).where(User.role == UserRole.admin).order_by(User.user_id).limit(1)
    )
    if user is None:
        raise HTTPException(
            status_code=500,
            detail="No admin user. Run scripts/bootstrap_admin.py first.",
        )
    return user


async def _load_products(session: AsyncSession) -> list[Product]:
    result = await session.execute(
        select(Product)
        .options(selectinload(Product.urls).selectinload(ProductURL.marketplace))
        .order_by(Product.created_at.desc())
    )
    return list(result.scalars().all())


async def _load_marketplaces(session: AsyncSession) -> list[Marketplace]:
    result = await session.execute(
        select(Marketplace).where(Marketplace.is_active.is_(True)).order_by(Marketplace.marketplace_id)
    )
    return list(result.scalars().all())


async def _url_states(session: AsyncSession, url_ids: list[int]) -> dict[int, UrlState]:
    if not url_ids:
        return {}
    runs_q = await session.execute(
        select(ParseRun)
        .where(ParseRun.url_id.in_(url_ids))
        .order_by(ParseRun.url_id, ParseRun.run_id.desc())
    )
    last_run_by_url: dict[int, ParseRun] = {}
    for run in runs_q.scalars():
        last_run_by_url.setdefault(run.url_id, run)

    counts_q = await session.execute(
        select(Review.url_id, Review.sentiment_label, func.count(Review.review_id))
        .where(Review.url_id.in_(url_ids))
        .group_by(Review.url_id, Review.sentiment_label)
    )
    by_url: dict[int, dict[SentimentLabel | None, int]] = {}
    for url_id, label, count in counts_q.all():
        by_url.setdefault(url_id, {})[label] = count

    states: dict[int, UrlState] = {}
    for uid in url_ids:
        d = by_url.get(uid, {})
        pos = d.get(SentimentLabel.positive, 0)
        neg = d.get(SentimentLabel.negative, 0)
        neu = d.get(SentimentLabel.neutral, 0)
        none_count = d.get(None, 0)
        states[uid] = UrlState(
            last_run=last_run_by_url.get(uid),
            review_count=pos + neg + neu + none_count,
            pos=pos,
            neg=neg,
            neu=neu,
            no_sentiment=none_count,
        )
    return states


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    async with async_session_maker() as session:
        products = await _load_products(session)
        marketplaces = await _load_marketplaces(session)
        url_ids = [u.url_id for p in products for u in p.urls]
        url_states = await _url_states(session, url_ids)
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "products": products,
            "marketplaces": marketplaces,
            "url_states": url_states,
        },
    )


@app.post("/products", response_class=HTMLResponse)
async def create_product(request: Request):
    form = await request.form()
    name = (form.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Product name is required.")

    async with async_session_maker() as session:
        user = await _default_user(session)
        product = Product(user_id=user.user_id, name=name)
        session.add(product)
        await session.flush()

        for i in range(1, 6):
            url_value = (form.get(f"url_{i}") or "").strip()
            mp_value = form.get(f"marketplace_{i}")
            if url_value and mp_value:
                session.add(
                    ProductURL(
                        product_id=product.product_id,
                        marketplace_id=int(mp_value),
                        url=url_value,
                    )
                )
        await session.commit()

        products = await _load_products(session)
        url_ids = [u.url_id for p in products for u in p.urls]
        url_states = await _url_states(session, url_ids)

    return templates.TemplateResponse(
        request,
        "_product_list.html",
        {"products": products, "url_states": url_states},
    )


@app.post("/urls/{url_id}/parse", response_class=HTMLResponse)
async def parse_url(url_id: int, request: Request):
    try:
        await run_parse(url_id)
    except Exception:
        # error is already persisted in parse_runs.error_message
        pass

    async with async_session_maker() as session:
        url = await session.scalar(
            select(ProductURL)
            .where(ProductURL.url_id == url_id)
            .options(selectinload(ProductURL.marketplace))
        )
        if url is None:
            raise HTTPException(status_code=404, detail="URL not found.")
        states = await _url_states(session, [url_id])

    return templates.TemplateResponse(
        request,
        "_url_row.html",
        {"url": url, "state": states[url_id]},
    )
