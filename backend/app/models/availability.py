"""Availability snapshot and source-check (audit) models."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utcnow
from app.models.enums import AvailabilityStatus


class AvailabilitySnapshot(Base):
    __tablename__ = "availability_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("event_sessions.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default=AvailabilityStatus.UNKNOWN.value, index=True
    )
    tickets_remaining: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sold_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_quota: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(60), default="48pedia")
    source_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
    raw_payload_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    session: Mapped["EventSession"] = relationship(back_populates="snapshots")

    __table_args__ = (
        Index("ix_snap_session_observed", "session_id", "observed_at"),
    )


class SourceCheck(Base):
    __tablename__ = "source_checks"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_name: Mapped[str] = mapped_column(String(60), index=True)
    endpoint_name: Mapped[str] = mapped_column(String(120))
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (Index("ix_source_check_name_checked", "source_name", "checked_at"),)
