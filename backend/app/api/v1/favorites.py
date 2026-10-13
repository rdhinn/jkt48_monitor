"""Favorite endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.deps import DbSession, ResolvedUser
from app.repositories import favorites as fav_repo
from app.repositories import members as member_repo
from app.schemas.member import MemberOut

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get("", response_model=list[MemberOut])
async def list_favorites(db: DbSession, user: ResolvedUser) -> list[MemberOut]:
    members = await fav_repo.list_for_user(db, user.id)
    return [
        MemberOut(**{**m.__dict__, "is_favorite": True}) for m in members
    ]


@router.post("/{member_id}", response_model=MemberOut)
async def add_favorite(member_id: int, db: DbSession, user: ResolvedUser) -> MemberOut:
    member = await member_repo.get_member(db, member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member tidak ditemukan.")
    await fav_repo.add(db, user.id, member_id)
    await db.commit()
    return MemberOut(**{**member.__dict__, "is_favorite": True})


@router.delete("/{member_id}")
async def remove_favorite(member_id: int, db: DbSession, user: ResolvedUser) -> dict:
    await fav_repo.remove(db, user.id, member_id)
    await db.commit()
    return {"detail": "Favorit dihapus."}
