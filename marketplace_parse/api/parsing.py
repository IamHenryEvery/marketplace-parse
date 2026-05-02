"""Parsing endpoints: trigger, status polling, analysis aggregates."""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from marketplace_parse.api.deps import (
    CurrentUser,
    get_owned_product_or_404,
    latest_analyses,
    parse_progress,
)
from marketplace_parse.api.schemas import (
    AnalysisItem,
    ParseTriggerOut,
    ProgressOut,
)
from marketplace_parse.db.enums import ParseStatus
from marketplace_parse.db.models import ParseRun, User
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
