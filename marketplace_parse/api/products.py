"""Product CRUD: list, create, read, partial-update, delete."""
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import selectinload

from marketplace_parse.api.deps import (
    CurrentUser,
    _product_to_out,
    get_owned_product_or_404,
    load_owned_product,
    load_user_products,
)
from marketplace_parse.api.schemas import (
    ProductCreate,
    ProductOut,
    ProductUpdate,
)
from marketplace_parse.db.models import Product, ProductURL, User
from marketplace_parse.db.session import async_session_maker


router = APIRouter()


@router.get("/products", response_model=list[ProductOut])
async def list_products(user: User = CurrentUser) -> list[ProductOut]:
    async with async_session_maker() as session:
        return await load_user_products(session, user.user_id)


@router.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product(body: ProductCreate, user: User = CurrentUser) -> ProductOut:
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Название обязательно")

    async with async_session_maker() as session:
        product = Product(user_id=user.user_id, name=body.name.strip())
        session.add(product)
        await session.flush()
        for u in body.urls:
            if not u.url.strip():
                continue
            session.add(
                ProductURL(
                    product_id=product.product_id,
                    marketplace_id=u.marketplace_id,
                    url=u.url.strip(),
                )
            )
        await session.commit()

        fresh = await load_owned_product(session, product.product_id, user.user_id)
        assert fresh is not None
        return _product_to_out(fresh)


@router.get("/products/{product_id}", response_model=ProductOut)
async def get_product(product_id: int, user: User = CurrentUser) -> ProductOut:
    async with async_session_maker() as session:
        product = await get_owned_product_or_404(session, product_id, user.user_id)
        return _product_to_out(product)


@router.patch("/products/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: int, body: ProductUpdate, user: User = CurrentUser
) -> ProductOut:
    async with async_session_maker() as session:
        product = await get_owned_product_or_404(session, product_id, user.user_id)

        if body.name is not None:
            new_name = body.name.strip()
            if not new_name:
                raise HTTPException(status_code=400, detail="Название не может быть пустым")
            product.name = new_name

        existing_by_id = {u.url_id: u for u in product.urls}

        for upd in body.urls_update or []:
            target = existing_by_id.get(upd.url_id)
            if target is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"url_id={upd.url_id} не принадлежит этому товару",
                )
            if upd.url is not None:
                if not upd.url.strip():
                    raise HTTPException(status_code=400, detail="URL не может быть пустым")
                target.url = upd.url.strip()
            if upd.marketplace_id is not None:
                target.marketplace_id = upd.marketplace_id

        for delete_id in body.urls_delete or []:
            target = existing_by_id.get(delete_id)
            if target is None:
                continue
            await session.delete(target)

        for new in body.urls_add or []:
            if not new.url.strip():
                continue
            session.add(
                ProductURL(
                    product_id=product_id,
                    marketplace_id=new.marketplace_id,
                    url=new.url.strip(),
                )
            )

        await session.commit()

    async with async_session_maker() as session:
        fresh = await load_owned_product(session, product_id, user.user_id)
        assert fresh is not None
        return _product_to_out(fresh)


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: int, user: User = CurrentUser) -> Response:
    async with async_session_maker() as session:
        product = await get_owned_product_or_404(session, product_id, user.user_id)
        await session.delete(product)
        await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
