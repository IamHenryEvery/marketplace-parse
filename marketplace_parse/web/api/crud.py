from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from marketplace_parse.db.models import Product, ProductURL
from marketplace_parse.db.session import async_session_maker
from marketplace_parse.web.api.deps import (
    get_current_user,
    load_marketplaces,
    load_owned_product,
    load_user_cards,
    require_user_or_redirect,
    templates,
)


router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> Response:
    user = await get_current_user(request)
    if (redirect := require_user_or_redirect(user)) is not None:
        return redirect
    async with async_session_maker() as session:
        cards = await load_user_cards(session, user.user_id)
    return templates.TemplateResponse(
        request, "index.html",
        {"current_user": user, "cards": cards},
    )


@router.get("/products/new", response_class=HTMLResponse)
async def new_product_modal(request: Request) -> Response:
    user = await get_current_user(request)
    if (redirect := require_user_or_redirect(user)) is not None:
        return redirect
    async with async_session_maker() as session:
        marketplaces = await load_marketplaces(session)
    return templates.TemplateResponse(
        request, "_create_modal.html", {"marketplaces": marketplaces}
    )


@router.get("/products/{product_id}", response_class=HTMLResponse)
async def product_modal(product_id: int, request: Request) -> Response:
    user = await get_current_user(request)
    if (redirect := require_user_or_redirect(user)) is not None:
        return redirect
    async with async_session_maker() as session:
        product = await load_owned_product(session, product_id, user.user_id)
    if product is None:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        request, "_product_modal.html", {"product": product}
    )


@router.get("/products/{product_id}/edit", response_class=HTMLResponse)
async def edit_product_modal(product_id: int, request: Request) -> Response:
    user = await get_current_user(request)
    if (redirect := require_user_or_redirect(user)) is not None:
        return redirect
    async with async_session_maker() as session:
        product = await load_owned_product(session, product_id, user.user_id)
        if product is None:
            raise HTTPException(status_code=404)
        marketplaces = await load_marketplaces(session)
    return templates.TemplateResponse(
        request, "_edit_modal.html",
        {"product": product, "marketplaces": marketplaces},
    )


@router.post("/products/{product_id}/edit", response_class=HTMLResponse)
async def edit_product(product_id: int, request: Request) -> Response:
    user = await get_current_user(request)
    if (redirect := require_user_or_redirect(user)) is not None:
        return redirect

    form = await request.form()
    name = (form.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Название обязательно.")

    async with async_session_maker() as session:
        product = await load_owned_product(session, product_id, user.user_id)
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
        cards = await load_user_cards(session, user.user_id)

    return templates.TemplateResponse(request, "_cards.html", {"cards": cards})


@router.delete("/products/{product_id}", response_class=HTMLResponse)
async def delete_product(product_id: int, request: Request) -> Response:
    user = await get_current_user(request)
    if (redirect := require_user_or_redirect(user)) is not None:
        return redirect
    async with async_session_maker() as session:
        product = await load_owned_product(session, product_id, user.user_id)
        if product is None:
            raise HTTPException(status_code=404)
        await session.delete(product)
        await session.commit()
        cards = await load_user_cards(session, user.user_id)
    return templates.TemplateResponse(request, "_cards.html", {"cards": cards})


@router.post("/products", response_class=HTMLResponse)
async def create_product(request: Request) -> Response:
    user = await get_current_user(request)
    if (redirect := require_user_or_redirect(user)) is not None:
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
        cards = await load_user_cards(session, user.user_id)

    return templates.TemplateResponse(request, "_cards.html", {"cards": cards})
