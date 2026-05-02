"""Lookup endpoint for the marketplaces dropdown."""
from fastapi import APIRouter
from sqlalchemy import select

from marketplace_parse.api.deps import CurrentUser
from marketplace_parse.api.schemas import MarketplaceOut
from marketplace_parse.db.models import Marketplace, User
from marketplace_parse.db.session import async_session_maker


router = APIRouter()


@router.get("/marketplaces", response_model=list[MarketplaceOut])
async def list_marketplaces(user: User = CurrentUser) -> list[MarketplaceOut]:
    async with async_session_maker() as session:
        result = await session.execute(
            select(Marketplace)
            .where(Marketplace.is_active.is_(True))
            .order_by(Marketplace.marketplace_id)
        )
        return [MarketplaceOut.model_validate(m) for m in result.scalars()]
