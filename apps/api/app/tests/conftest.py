"""Pytest fixtures: isolated SQLite DB + HTTP client bound to the ASGI app."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_app.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database.base import Base
from app.database.session import engine
from app.modules.auth import models  # noqa: F401  (register tables)
from app.server import app


@pytest_asyncio.fixture(autouse=True)
async def _reset_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
