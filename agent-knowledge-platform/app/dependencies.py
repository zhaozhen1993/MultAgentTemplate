"""FastAPI dependency injection utilities."""

from typing import Optional
from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.core.exceptions import AuthenticationError
from app.db.session import get_db


async def get_current_user_id(
    authorization: Optional[str] = Header(None),
) -> UUID:
    """Extract and validate the current user from JWT token."""
    if not authorization:
        raise AuthenticationError("Authorization header missing")

    # Support both "Bearer xxx" and raw token
    token = authorization
    if authorization.startswith("Bearer "):
        token = authorization[7:]

    payload = decode_token(token)
    if payload is None:
        raise AuthenticationError("Invalid or expired token")

    if payload.get("type") != "access":
        raise AuthenticationError("Invalid token type")

    try:
        user_id = UUID(payload["sub"])
    except (KeyError, ValueError):
        raise AuthenticationError("Invalid token payload")

    return user_id


async def get_current_admin_id(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> UUID:
    """Verify the current user is an admin."""
    from app.models.user import User
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_admin:
        from app.core.exceptions import AuthorizationError
        raise AuthorizationError("Admin access required")

    return user_id
