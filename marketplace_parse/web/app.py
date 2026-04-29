from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.middleware.sessions import SessionMiddleware

from datetime import datetime, timezone

from marketplace_parse.core.config import settings
from marketplace_parse.core.security import hash_password, verify_password
from marketplace_parse.db.enums import ParseStatus, UserRole
from marketplace_parse.db.models import (
    AnalysisResult,
    Marketplace,
    ParseRun,
    Product,
    ProductURL,
    User,
)
from marketplace_parse.db.session import async_session_maker
from marketplace_parse.mq import publish_parse_task
from marketplace_parse.parsers.runner import enqueue_parse


TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

app = FastAPI(title="marketplace-parse (dev)")
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret)


@dataclass
class ProductCard:
    product: Product
    marketplaces: list[Marketplace]


# ---------- auth helpers ----------

async def get_current_user(request: Request) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    async with async_session_maker() as session:
        return await session.get(User, user_id)


def _require_user_or_redirect(user: User | None) -> RedirectResponse | None:
    if user is None:
        return RedirectResponse("/login", status_code=303)
    return None


# ---------- data loading ----------

async def _load_user_cards(session: AsyncSession, user_id: int) -> list[ProductCard]:
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


async def _load_marketplaces(session: AsyncSession) -> list[Marketplace]:
    result = await session.execute(
        select(Marketplace)
        .where(Marketplace.is_active.is_(True))
        .order_by(Marketplace.marketplace_id)
    )
    return list(result.scalars().all())


async def _load_owned_product(
    session: AsyncSession, product_id: int, user_id: int
) -> Product | None:
    return await session.scalar(
        select(Product)
        .where(Product.product_id == product_id, Product.user_id == user_id)
        .options(selectinload(Product.urls).selectinload(ProductURL.marketplace))
    )


async def _latest_analyses(
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


# ---------- auth routes ----------

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request) -> Response:
    return templates.TemplateResponse(request, "register.html", {"error": None})


@app.post("/register")
async def register(request: Request) -> Response:
    form = await request.form()
    email = (form.get("email") or "").strip().lower()
    password = form.get("password") or ""
    if not email or not password:
        return templates.TemplateResponse(
            request, "register.html",
            {"error": "Email и пароль обязательны."},
            status_code=400,
        )
    async with async_session_maker() as session:
        existing = await session.scalar(select(User).where(User.email == email))
        if existing is not None:
            return templates.TemplateResponse(
                request, "register.html",
                {"error": "Этот email уже занят."},
                status_code=400,
            )
        user = User(
            email=email,
            password_hash=hash_password(password),
            role=UserRole.user,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        request.session["user_id"] = user.user_id
    return RedirectResponse("/", status_code=303)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> Response:
    return templates.TemplateResponse(request, "login.html", {"error": None})


@app.post("/login")
async def login(request: Request) -> Response:
    form = await request.form()
    email = (form.get("email") or "").strip().lower()
    password = form.get("password") or ""
    async with async_session_maker() as session:
        user = await session.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request, "login.html",
            {"error": "Неверный email или пароль."},
            status_code=400,
        )
    request.session["user_id"] = user.user_id
    return RedirectResponse("/", status_code=303)


@app.get("/logout")
async def logout(request: Request) -> Response:
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


# ---------- index ----------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> Response:
    user = await get_current_user(request)
    if (redirect := _require_user_or_redirect(user)) is not None:
        return redirect
    async with async_session_maker() as session:
        cards = await _load_user_cards(session, user.user_id)
    return templates.TemplateResponse(
        request,
        "index.html",
        {"current_user": user, "cards": cards},
    )


# ---------- product modals ----------

@app.get("/products/new", response_class=HTMLResponse)
async def new_product_modal(request: Request) -> Response:
    user = await get_current_user(request)
    if (redirect := _require_user_or_redirect(user)) is not None:
        return redirect
    async with async_session_maker() as session:
        marketplaces = await _load_marketplaces(session)
    return templates.TemplateResponse(
        request, "_create_modal.html", {"marketplaces": marketplaces}
    )


@app.get("/products/{product_id}", response_class=HTMLResponse)
async def product_modal(product_id: int, request: Request) -> Response:
    user = await get_current_user(request)
    if (redirect := _require_user_or_redirect(user)) is not None:
        return redirect
    async with async_session_maker() as session:
        product = await _load_owned_product(session, product_id, user.user_id)
    if product is None:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        request, "_product_modal.html", {"product": product}
    )


@app.get("/products/{product_id}/edit", response_class=HTMLResponse)
async def edit_product_modal(product_id: int, request: Request) -> Response:
    user = await get_current_user(request)
    if (redirect := _require_user_or_redirect(user)) is not None:
        return redirect
    async with async_session_maker() as session:
        product = await _load_owned_product(session, product_id, user.user_id)
        if product is None:
            raise HTTPException(status_code=404)
        marketplaces = await _load_marketplaces(session)
    return templates.TemplateResponse(
        request, "_edit_modal.html",
        {"product": product, "marketplaces": marketplaces},
    )


@app.post("/products/{product_id}/edit", response_class=HTMLResponse)
async def edit_product(product_id: int, request: Request) -> Response:
    user = await get_current_user(request)
    if (redirect := _require_user_or_redirect(user)) is not None:
        return redirect

    form = await request.form()
    name = (form.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Название обязательно.")

    async with async_session_maker() as session:
        product = await _load_owned_product(session, product_id, user.user_id)
        if product is None:
            raise HTTPException(status_code=404)
        product.name = name

        for url in list(product.urls):
            if form.get(f"delete_{url.url_id}"):
                await session.delete(url)
                continue
            new_url_value = (form.get(f"existing_url_{url.url_id}") or "").strip()
            new_mp_value = form.get(f"existing_marketplace_{url.url_id}")
            if new_url_value:
                url.url = new_url_value
            if new_mp_value:
                url.marketplace_id = int(new_mp_value)

        for i in range(1, 6):
            new_url_value = (form.get(f"new_url_{i}") or "").strip()
            new_mp_value = form.get(f"new_marketplace_{i}")
            if new_url_value and new_mp_value:
                session.add(
                    ProductURL(
                        product_id=product_id,
                        marketplace_id=int(new_mp_value),
                        url=new_url_value,
                    )
                )

        await session.commit()
        cards = await _load_user_cards(session, user.user_id)

    return templates.TemplateResponse(request, "_cards.html", {"cards": cards})


@app.delete("/products/{product_id}", response_class=HTMLResponse)
async def delete_product(product_id: int, request: Request) -> Response:
    user = await get_current_user(request)
    if (redirect := _require_user_or_redirect(user)) is not None:
        return redirect
    async with async_session_maker() as session:
        product = await _load_owned_product(session, product_id, user.user_id)
        if product is None:
            raise HTTPException(status_code=404)
        await session.delete(product)
        await session.commit()
        cards = await _load_user_cards(session, user.user_id)
    return templates.TemplateResponse(request, "_cards.html", {"cards": cards})


@app.post("/products", response_class=HTMLResponse)
async def create_product(request: Request) -> Response:
    user = await get_current_user(request)
    if (redirect := _require_user_or_redirect(user)) is not None:
        return redirect

    form = await request.form()
    name = (form.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Название обязательно.")

    async with async_session_maker() as session:
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
        cards = await _load_user_cards(session, user.user_id)

    return templates.TemplateResponse(request, "_cards.html", {"cards": cards})


# ---------- parse + analysis ----------

@app.post("/products/{product_id}/parse", response_class=HTMLResponse)
async def parse_product(product_id: int, request: Request) -> Response:
    user = await get_current_user(request)
    if (redirect := _require_user_or_redirect(user)) is not None:
        return redirect

    async with async_session_maker() as session:
        product = await _load_owned_product(session, product_id, user.user_id)
        if product is None:
            raise HTTPException(status_code=404)
        url_ids = [u.url_id for u in product.urls]

    if not url_ids:
        raise HTTPException(status_code=400, detail="У товара нет ссылок.")

    for url_id in url_ids:
        run_id: int | None = None
        try:
            run_id, slug = await enqueue_parse(url_id)
            await publish_parse_task(run_id, slug)
        except Exception as exc:
            if run_id is not None:
                async with async_session_maker() as session:
                    run = await session.get(ParseRun, run_id)
                    if run is not None and run.status == ParseStatus.pending:
                        run.status = ParseStatus.failed
                        run.error_message = f"enqueue failed: {exc!r}"
                        run.finished_at = datetime.now(timezone.utc)
                        await session.commit()

    async with async_session_maker() as session:
        product = await _load_owned_product(session, product_id, user.user_id)
        progress = await _parse_progress(session, product_id)

    return templates.TemplateResponse(
        request,
        "_parse_progress_modal.html",
        {"product": product, **progress},
    )


@app.get("/products/{product_id}/parse/status", response_class=HTMLResponse)
async def parse_status(product_id: int, request: Request) -> Response:
    user = await get_current_user(request)
    if (redirect := _require_user_or_redirect(user)) is not None:
        return redirect

    async with async_session_maker() as session:
        product = await _load_owned_product(session, product_id, user.user_id)
        if product is None:
            raise HTTPException(status_code=404)
        progress = await _parse_progress(session, product_id)

        if progress["total"] > 0 and progress["in_flight"] == 0:
            analyses = await _latest_analyses(session, product_id)
            return templates.TemplateResponse(
                request,
                "_analysis_modal.html",
                {"product": product, "analyses": analyses},
            )

    return templates.TemplateResponse(
        request,
        "_parse_progress_modal.html",
        {"product": product, **progress},
    )


async def _parse_progress(session: AsyncSession, product_id: int) -> dict:
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
