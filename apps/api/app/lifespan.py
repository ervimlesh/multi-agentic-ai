"""Application lifespan — startup/shutdown hooks."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables exist.
    await init_db()
    yield
    # Shutdown: nothing to clean up yet.
