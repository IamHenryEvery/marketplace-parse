import os

os.environ["POSTGRES_DB"] = "marketplace_parse_test"

import asyncio
from pathlib import Path

import asyncpg
import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text

from marketplace_parse.app import app
from marketplace_parse.core.config import settings
from marketplace_parse.db.base import Base
from marketplace_parse.db.enums import UserRole
from marketplace_parse.db.models import Marketplace, User
from marketplace_parse.db.session import async_session_maker, engine

REPO_ROOT = Path(__file__).resolve().parent.parent

# Reference data seeded by alembic; kept across tests to avoid re-seeding.
EXCLUDED_FROM_TRUNCATE = {"marketplaces"}


async def _ensure_test_db_exists() -> None:
    sys_dsn = (
        f"postgresql://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/postgres"
    )
    conn = await asyncpg.connect(sys_dsn)
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            settings.postgres_db,
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{settings.postgres_db}"')
    finally:
        await conn.close()


_MARKETPLACE_SEEDS = [
    ("yandex_market", "Яндекс Маркет"),
    ("ozon", "Ozon"),
    ("wildberries", "Wildberries"),
    ("megamarket", "МегаМаркет"),
]


async def _seed_marketplaces() -> None:
    # asyncpg directly (not the global SQLAlchemy engine): touching `engine`
    # here would bind its pool to this throwaway loop, breaking later tests.
    dsn = (
        f"postgresql://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )
    conn = await asyncpg.connect(dsn)
    try:
        for slug, display_name in _MARKETPLACE_SEEDS:
            await conn.execute(
                "INSERT INTO marketplaces (slug, display_name) "
                "VALUES ($1, $2) ON CONFLICT (slug) DO NOTHING",
                slug,
                display_name,
            )
    finally:
        await conn.close()


@pytest.fixture(scope="session", autouse=True)
def _setup_test_db():
    asyncio.run(_ensure_test_db_exists())
    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    command.upgrade(cfg, "head")
    asyncio.run(_seed_marketplaces())
    yield


@pytest_asyncio.fixture(autouse=True)
async def _truncate_tables(_setup_test_db):
    tables = ", ".join(
        f'"{t.name}"'
        for t in reversed(Base.metadata.sorted_tables)
        if t.name not in EXCLUDED_FROM_TRUNCATE
    )
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    yield


async def _make_anon_client() -> AsyncClient:
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def _register(ac: AsyncClient, email: str, password: str = "secret123") -> int:
    resp = await ac.post(
        "/api/auth/register",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["user_id"]


@pytest_asyncio.fixture
async def client():
    async with await _make_anon_client() as ac:
        yield ac


@pytest_asyncio.fixture
async def user_client():
    async with await _make_anon_client() as ac:
        await _register(ac, "user@example.com")
        yield ac


@pytest_asyncio.fixture
async def other_user_client():
    async with await _make_anon_client() as ac:
        await _register(ac, "other@example.com")
        yield ac


@pytest_asyncio.fixture
async def admin_client():
    async with await _make_anon_client() as ac:
        await _register(ac, "admin@example.com", "adminpass")
        async with async_session_maker() as session:
            user = await session.scalar(
                select(User).where(User.email == "admin@example.com")
            )
            user.role = UserRole.admin
            await session.commit()
        yield ac


@pytest_asyncio.fixture
async def marketplace_id() -> int:
    async with async_session_maker() as session:
        mp = await session.scalar(
            select(Marketplace).where(Marketplace.is_active.is_(True)).limit(1)
        )
        assert mp is not None, "no active marketplace seeded — check alembic"
        return mp.marketplace_id
