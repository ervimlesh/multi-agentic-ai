"""CONTROLLER layer — auth HTTP endpoints."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth_dependency import get_current_user
from app.api.dependencies.db_dependency import get_db
from app.modules.auth.models import User
from app.modules.auth.schemas import (
    AuthResponse,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED
)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Create a new account and return the user with a fresh token pair."""
    return await AuthService(db).register(data)


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate with email + password and return a token pair."""
    return await AuthService(db).login(data)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Rotate a refresh token for a new access + refresh pair."""
    return await AuthService(db).refresh(data.refresh_token)


@router.post("/logout", response_model=MessageResponse)
async def logout(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Revoke a refresh token."""
    await AuthService(db).logout(data.refresh_token)
    return MessageResponse(message="Successfully logged out")


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user."""
    return current_user
