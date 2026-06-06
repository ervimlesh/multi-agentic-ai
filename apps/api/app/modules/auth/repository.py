"""REPOSITORY layer — all database access for auth lives here."""
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import OtpCode, RefreshToken, User


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---- Users ----
    async def get_user_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: str) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create_user(self, email: str, full_name: str) -> User:
        user = User(email=email, full_name=full_name)
        self.session.add(user)
        await self.session.flush()
        return user

    # ---- OTP codes ----
    async def create_otp(
        self, email: str, code_hash: str, purpose: str, expires_at: datetime
    ) -> OtpCode:
        otp = OtpCode(
            email=email,
            code_hash=code_hash,
            purpose=purpose,
            expires_at=expires_at,
        )
        self.session.add(otp)
        await self.session.flush()
        return otp

    async def get_latest_active_otp(self, email: str) -> OtpCode | None:
        result = await self.session.execute(
            select(OtpCode)
            .where(OtpCode.email == email, OtpCode.consumed.is_(False))
            .order_by(OtpCode.created_at.desc())
        )
        return result.scalars().first()

    async def invalidate_otps(self, email: str) -> None:
        """Consume any outstanding codes for an email before issuing a new one."""
        await self.session.execute(
            update(OtpCode)
            .where(OtpCode.email == email, OtpCode.consumed.is_(False))
            .values(consumed=True)
        )
        await self.session.flush()

    # ---- Refresh tokens ----
    async def store_refresh_token(
        self, user_id: str, token_hash: str, expires_at: datetime
    ) -> RefreshToken:
        token = RefreshToken(
            user_id=user_id, token_hash=token_hash, expires_at=expires_at
        )
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_refresh_token(self, token_hash: str) -> RefreshToken | None:
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def revoke_refresh_token(self, token: RefreshToken) -> None:
        token.revoked = True
        await self.session.flush()

    async def revoke_all_user_tokens(self, user_id: str) -> None:
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
            .values(revoked=True)
        )
        await self.session.flush()
