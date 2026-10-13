"""Favorite queries."""
from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Favorite, Member


async def list_for_user(db: AsyncSession, user_id: int) -> list[Member]:
    stmt = (
        select(Member)
        .join(Favorite, Favorite.member_id == Member.id)
        .where(Favorite.user_id == user_id)
        .order_by(Member.name.asc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def member_ids(db: AsyncSession, user_id: int) -> set[int]:
    stmt = select(Favorite.member_id).where(Favorite.user_id == user_id)
    return set((await db.execute(stmt)).scalars().all())


async def add(db: AsyncSession, user_id: int, member_id: int) -> Favorite:
    existing = (
        await db.execute(
            select(Favorite).where(
                Favorite.user_id == user_id, Favorite.member_id == member_id
            )
        )
    ).scalar_one_or_none()
    if existing:
        return existing
    fav = Favorite(user_id=user_id, member_id=member_id)
    db.add(fav)
    await db.flush()
    return fav


async def remove(db: AsyncSession, user_id: int, member_id: int) -> None:
    await db.execute(
        delete(Favorite).where(
            Favorite.user_id == user_id, Favorite.member_id == member_id
        )
    )
