"""Shared FastAPI dependencies."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.init_db import ensure_default_user
from app.db.session import get_session
from app.models import User

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_session)]
OptionalCreds = Annotated[
    HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
]


async def _user_from_token(db: AsyncSession, creds: OptionalCreds) -> User | None:
    if creds is None:
        return None
    payload = decode_access_token(creds.credentials)
    if not payload:
        return None
    username = payload.get("sub")
    if not username:
        return None
    from sqlalchemy import select

    stmt = select(User).where(User.username == username)
    return (await db.execute(stmt)).scalar_one_or_none()


async def current_user_optional(db: DbSession, creds: OptionalCreds) -> User | None:
    return await _user_from_token(db, creds)


async def current_user_required(db: DbSession, creds: OptionalCreds) -> User:
    user = await _user_from_token(db, creds)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autentikasi diperlukan.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def resolve_user(db: DbSession, creds: OptionalCreds) -> User:
    """Authenticated user, or the local default account in single-user mode."""
    user = await _user_from_token(db, creds)
    if user is not None:
        return user
    return await ensure_default_user(db)


CurrentUser = Annotated[User, Depends(current_user_required)]
ResolvedUser = Annotated[User, Depends(resolve_user)]
