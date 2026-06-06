"""SERVICE layer — passwordless OTP authentication business logic."""
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.auth import otp as otp_utils
from app.modules.auth import tokens as token_utils
from app.modules.auth.models import User
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import (
    AuthResponse,
    LoginRequest,
    OtpSentResponse,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AuthRepository(session)

    # ---------- OTP issuance ----------
    async def _issue_otp(self, email: str, purpose: str) -> OtpSentResponse:
        # Cooldown: block rapid re-requests.
        latest = await self.repo.get_latest_active_otp(email)
        if latest is not None:
            age = (_now() - _aware(latest.created_at)).total_seconds()
            if age < settings.OTP_RESEND_COOLDOWN_SECONDS:
                wait = int(settings.OTP_RESEND_COOLDOWN_SECONDS - age)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Please wait {wait}s before requesting a new code",
                )

        await self.repo.invalidate_otps(email)
        code = otp_utils.generate_code()
        expires_at = _now() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
        await self.repo.create_otp(
            email=email,
            code_hash=otp_utils.hash_code(code),
            purpose=purpose,
            expires_at=expires_at,
        )
        await self.session.commit()
        await otp_utils.deliver_otp(email, code, purpose)
        return OtpSentResponse(
            message="Verification code sent",
            email=email,
            expires_in=settings.OTP_EXPIRE_MINUTES * 60,
        )

    async def request_register(self, data: RegisterRequest) -> OtpSentResponse:
        existing = await self.repo.get_user_by_email(data.email)
        if existing and existing.is_verified:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered. Please sign in instead.",
            )
        if not existing:
            await self.repo.create_user(email=data.email, full_name=data.full_name)
            await self.session.commit()
        return await self._issue_otp(data.email, purpose="register")

    async def request_login(self, data: LoginRequest) -> OtpSentResponse:
        user = await self.repo.get_user_by_email(data.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No account found for this email. Please sign up.",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled"
            )
        return await self._issue_otp(data.email, purpose="login")

    async def resend(self, email: str) -> OtpSentResponse:
        user = await self.repo.get_user_by_email(email)
        purpose = "login" if (user and user.is_verified) else "register"
        return await self._issue_otp(email, purpose=purpose)

    # ---------- Verification ----------
    async def verify(self, email: str, code: str) -> AuthResponse:
        invalid = HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code",
        )
        otp = await self.repo.get_latest_active_otp(email)
        if otp is None:
            raise invalid
        if _aware(otp.expires_at) < _now():
            raise invalid
        if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
            otp.consumed = True
            await self.session.commit()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts. Request a new code.",
            )

        if not otp_utils.verify_code(code, otp.code_hash):
            otp.attempts += 1
            await self.session.commit()
            raise invalid

        otp.consumed = True

        user = await self.repo.get_user_by_email(email)
        if user is None:
            # Defensive: shouldn't happen because request_* create the user.
            raise invalid
        user.is_verified = True

        tokens = await self._issue_tokens(user)
        await self.session.commit()
        await self.session.refresh(user)
        return AuthResponse(user=UserResponse.model_validate(user), tokens=tokens)

    # ---------- Tokens ----------
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
        if _aware(stored.expires_at) < _now():
            raise unauthorized

        user = await self.repo.get_user_by_id(payload["sub"])
        if not user or not user.is_active:
            raise unauthorized

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
