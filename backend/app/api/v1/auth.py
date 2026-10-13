"""Authentication endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession
from app.core.security import create_access_token, verify_password
from app.models import User
from app.schemas.dashboard import LoginIn, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=TokenOut)
async def login(payload: LoginIn, db: DbSession) -> TokenOut:
    stmt = select(User).where(User.username == payload.username)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username atau password salah.",
        )
    return TokenOut(access_token=create_access_token(user.username))
