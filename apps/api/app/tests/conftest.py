"""Pytest fixtures: isolated SQLite DB, HTTP client, and OTP capture."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_app.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-at-least-32-bytes-long!!")
os.environ.setdefault("OTP_RESEND_COOLDOWN_SECONDS", "0")

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database.base import Base
from app.database.session import engine
from app.modules.auth import models  # noqa: F401  (register tables)
from app.modules.auth import otp as otp_utils
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
async def otp_box(monkeypatch):
    """Capture OTP codes instead of emailing them. Keyed by email."""
    box: dict[str, str] = {}

    async def _capture(email: str, code: str, purpose: str = "login") -> None:
        box[email] = code

    monkeypatch.setattr(otp_utils, "deliver_otp", _capture)
    return box


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
