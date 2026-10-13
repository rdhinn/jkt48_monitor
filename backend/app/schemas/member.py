"""Member schemas."""
from __future__ import annotations

from datetime import datetime

from app.schemas.common import ORMModel


class MemberOut(ORMModel):
    id: int
    external_id: str
    name: str
    nickname: str | None = None
    team_code: str | None = None
    generation_code: str | None = None
    image_url: str | None = None
    is_active: bool
    source: str
    updated_at: datetime | None = None
    is_favorite: bool = False


class MemberDetailOut(MemberOut):
    total_sessions: int = 0
    sessions_available: int = 0
    tickets_remaining: int | None = None
