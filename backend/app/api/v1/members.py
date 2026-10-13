"""Member endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import DbSession, ResolvedUser
from app.repositories import availability as availability_repo
from app.repositories import favorites as fav_repo
from app.repositories import members as member_repo
from app.schemas.common import Page
from app.schemas.member import MemberDetailOut, MemberOut

router = APIRouter(prefix="/members", tags=["members"])


@router.get("", response_model=Page[MemberOut])
async def list_members(
    db: DbSession,
    user: ResolvedUser,
    q: str | None = Query(None, description="Search by name/nickname"),
    team: str | None = None,
    generation: str | None = None,
    active_only: bool = True,
    favorites_only: bool = False,
    event_id: int | None = None,
    status: str | None = Query(None, description="Filter by latest availability status"),
    category: str | None = Query(None, description="video_call | meet_greet | two_shot"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
) -> Page[MemberOut]:
    fav_ids = await fav_repo.member_ids(db, user.id)
    restrict: set[int] | None = None
    if event_id or status or category:
        restrict = await availability_repo.member_ids_matching(
            db, event_id=event_id, status=status, category=category
        )
    if favorites_only:
        restrict = (restrict or set()) & fav_ids if restrict is not None else set(fav_ids)

    members, total = await member_repo.list_members(
        db,
        q=q,
        team=team,
        generation=generation,
        active_only=active_only,
        offset=(page - 1) * per_page,
        limit=per_page,
    )
    if restrict is not None:
        members = [m for m in members if m.id in restrict]
        # Note: total is a pre-filter count; recompute for accuracy
        all_members, _ = await member_repo.list_members(
            db, q=q, team=team, generation=generation, active_only=active_only,
            offset=0, limit=10000,
        )
        total = sum(1 for m in all_members if m.id in restrict)

    items = [
        MemberOut(**{**m.__dict__, "is_favorite": m.id in fav_ids})
        for m in members
    ]
    return Page[MemberOut](items=items, total=total, page=page, per_page=per_page)


@router.get("/{member_id}", response_model=MemberDetailOut)
async def get_member(member_id: int, db: DbSession, user: ResolvedUser) -> MemberDetailOut:
    member = await member_repo.get_member(db, member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member tidak ditemukan.")
    fav_ids = await fav_repo.member_ids(db, user.id)
    summary = await availability_repo.member_availability_summary(db, member_id)
    return MemberDetailOut(
        **{**member.__dict__, "is_favorite": member.id in fav_ids}, **summary
    )
