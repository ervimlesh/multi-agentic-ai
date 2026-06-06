"""Async SQLAlchemy engine + session factory and DB initialization."""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.database.base import Base

engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


async def init_db() -> None:
    """Create all tables. Imports models so they register on the metadata."""
    # Importing the models module registers the tables on Base.metadata.
    from app.modules.auth import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session and ensure it is closed afterwards."""
    async with AsyncSessionLocal() as session:
        yield session
