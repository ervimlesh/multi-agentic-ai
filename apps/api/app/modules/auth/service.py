"""SERVICE layer — business logic for authentication."""
from datetime import datetime, timezone

import jwt
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth import tokens as token_utils
from app.modules.auth.models import User
from app.modules.auth.password import hash_password, verify_password
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)


def _aware(dt: datetime) -> datetime:
    """Normalize a possibly-naive datetime (SQLite) to UTC-aware."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AuthRepository(session)

    async def _issue_tokens(self, user: User) -> TokenResponse:
        access, expires_in = token_utils.create_access_token(
            user.id, {"email": user.email}
        )
        refresh, refresh_exp = token_utils.create_refresh_token(user.id)
        await self.repo.store_refresh_token(
            user.id, token_utils.hash_token(refresh), refresh_exp
        )
        return TokenResponse(
            access_token=access, refresh_token=refresh, expires_in=expires_in
        )

    async def register(self, data: RegisterRequest) -> AuthResponse:
        if await self.repo.get_user_by_email(data.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        user = await self.repo.create_user(
            email=data.email,
            full_name=data.full_name,
            hashed_password=hash_password(data.password),
        )
        tokens = await self._issue_tokens(user)
        await self.session.commit()
        await self.session.refresh(user)
        return AuthResponse(user=UserResponse.model_validate(user), tokens=tokens)

    async def login(self, data: LoginRequest) -> AuthResponse:
        user = await self.repo.get_user_by_email(data.email)
        if not user or not verify_password(data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled",
            )
        tokens = await self._issue_tokens(user)
        await self.session.commit()
        return AuthResponse(user=UserResponse.model_validate(user), tokens=tokens)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        unauthorized = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
        try:
            payload = token_utils.decode_token(refresh_token)
        except jwt.PyJWTError:
            raise unauthorized
        if payload.get("type") != "refresh":
            raise unauthorized

        stored = await self.repo.get_refresh_token(
            token_utils.hash_token(refresh_token)
        )
        if not stored or stored.revoked:
            raise unauthorized
        if _aware(stored.expires_at) < datetime.now(timezone.utc):
            raise unauthorized

        user = await self.repo.get_user_by_id(payload["sub"])
        if not user or not user.is_active:
            raise unauthorized

        # Rotate: revoke the used token and issue a fresh pair.
        await self.repo.revoke_refresh_token(stored)
        tokens = await self._issue_tokens(user)
        await self.session.commit()
        return tokens

    async def logout(self, refresh_token: str) -> None:
        stored = await self.repo.get_refresh_token(
            token_utils.hash_token(refresh_token)
        )
        if stored and not stored.revoked:
            await self.repo.revoke_refresh_token(stored)
            await self.session.commit()
