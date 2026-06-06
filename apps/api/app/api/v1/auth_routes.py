"""CONTROLLER layer — passwordless OTP auth endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth_dependency import get_current_user
from app.api.dependencies.db_dependency import get_db
from app.modules.auth.models import User
from app.modules.auth.schemas import (
    AuthResponse,
    LoginRequest,
    MessageResponse,
    OtpSentResponse,
    RefreshRequest,
    RegisterRequest,
    ResendRequest,
    TokenResponse,
    UserResponse,
    VerifyRequest,
)
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=OtpSentResponse)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Step 1 (sign up): create the pending account and email an OTP."""
    return await AuthService(db).request_register(data)


@router.post("/login", response_model=OtpSentResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Step 1 (sign in): email an OTP to an existing account."""
    return await AuthService(db).request_login(data)


@router.post("/verify", response_model=AuthResponse)
async def verify(data: VerifyRequest, db: AsyncSession = Depends(get_db)):
    """Step 2: verify the OTP and return the user + token pair."""
    return await AuthService(db).verify(data.email, data.code)


@router.post("/resend", response_model=OtpSentResponse)
async def resend(data: ResendRequest, db: AsyncSession = Depends(get_db)):
    """Re-send a fresh OTP (subject to cooldown)."""
    return await AuthService(db).resend(data.email)


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
