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
from marketplace_parse.db.models import User
from marketplace_parse.db.session import async_session_maker, engine

REPO_ROOT = Path(__file__).resolve().parent.parent


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


@pytest.fixture(scope="session", autouse=True)
def _setup_test_db():
    asyncio.run(_ensure_test_db_exists())
    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    command.upgrade(cfg, "head")
    yield


@pytest_asyncio.fixture(autouse=True)
async def _truncate_tables(_setup_test_db):
    tables = ", ".join(f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables))
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    yield


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def user_client(client):
    resp = await client.post(
        "/api/auth/register",
        json={"email": "user@example.com", "password": "secret123"},
    )
    assert resp.status_code == 200, resp.text
    return client


@pytest_asyncio.fixture
async def admin_client(client):
    resp = await client.post(
        "/api/auth/register",
        json={"email": "admin@example.com", "password": "adminpass"},
    )
    assert resp.status_code == 200, resp.text
    async with async_session_maker() as session:
        user = await session.scalar(
            select(User).where(User.email == "admin@example.com")
        )
        user.role = UserRole.admin
        await session.commit()
    return client
