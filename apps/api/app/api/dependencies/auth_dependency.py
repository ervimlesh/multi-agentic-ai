"""Auth dependency — resolves the current user from a Bearer access token."""
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.db_dependency import get_db
from app.modules.auth import tokens as token_utils
from app.modules.auth.models import User
from app.modules.auth.repository import AuthRepository

bearer_scheme = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = token_utils.decode_token(credentials.credentials)
    except jwt.PyJWTError:
        raise unauthorized

    if payload.get("type") != "access":
        raise unauthorized

    user = await AuthRepository(db).get_user_by_id(payload.get("sub", ""))
    if not user or not user.is_active:
        raise unauthorized
    return user
