from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from marketplace_parse.db.enums import ParseStatus
from marketplace_parse.db.models import ParseRun
from marketplace_parse.db.session import async_session_maker
from marketplace_parse.mq import publish_parse_task
from marketplace_parse.parsers.runner import enqueue_parse
from marketplace_parse.web.api.deps import (
    get_current_user,
    latest_analyses,
    load_owned_product,
    parse_progress,
    require_user_or_redirect,
    templates,
)


router = APIRouter()


@router.post("/products/{product_id}/parse", response_class=HTMLResponse)
async def parse_product(product_id: int, request: Request) -> Response:
    user = await get_current_user(request)
    if (redirect := require_user_or_redirect(user)) is not None:
        return redirect

    async with async_session_maker() as session:
        product = await load_owned_product(session, product_id, user.user_id)
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
        product = await load_owned_product(session, product_id, user.user_id)
        progress = await parse_progress(session, product_id)

    return templates.TemplateResponse(
        request, "_parse_progress_modal.html",
        {"product": product, **progress},
    )


@router.get("/products/{product_id}/parse/status", response_class=HTMLResponse)
async def parse_status(product_id: int, request: Request) -> Response:
    user = await get_current_user(request)
    if (redirect := require_user_or_redirect(user)) is not None:
        return redirect

    async with async_session_maker() as session:
        product = await load_owned_product(session, product_id, user.user_id)
        if product is None:
            raise HTTPException(status_code=404)
        progress = await parse_progress(session, product_id)

        if progress["total"] > 0 and progress["in_flight"] == 0:
            analyses = await latest_analyses(session, product_id)
            return templates.TemplateResponse(
                request, "_analysis_modal.html",
                {"product": product, "analyses": analyses},
            )

    return templates.TemplateResponse(
        request, "_parse_progress_modal.html",
        {"product": product, **progress},
    )
