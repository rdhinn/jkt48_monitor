"""Member model."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Member(Base, TimestampMixin):
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    nickname: Mapped[str | None] = mapped_column(String(200), nullable=True)
    team_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    generation_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(String(60), default="48pedia")
    source_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
