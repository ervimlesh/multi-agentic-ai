"""JWT access/refresh token creation and decoding."""
import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(subject: str, extra: dict | None = None) -> tuple[str, int]:
    """Return (token, expires_in_seconds)."""
    expire = _now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": subject,
        "type": "access",
        "iat": _now(),
        "exp": expire,
        "jti": str(uuid.uuid4()),
    }
    if extra:
        payload.update(extra)
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60


def create_refresh_token(subject: str) -> tuple[str, datetime]:
    """Return (token, expires_at)."""
    expire = _now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": subject,
        "type": "refresh",
        "iat": _now(),
        "exp": expire,
        "jti": str(uuid.uuid4()),
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, expire


def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises jwt.PyJWTError on failure."""
    return jwt.decode(
        token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )


def hash_token(token: str) -> str:
    """SHA-256 hash used to store refresh tokens at rest."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
