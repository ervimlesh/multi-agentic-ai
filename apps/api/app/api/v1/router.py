"""Aggregates all v1 routers."""
from fastapi import APIRouter

from app.api.v1 import auth_routes

api_router = APIRouter()
api_router.include_router(auth_routes.router)
