"""Event and event-session models."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import EntryType, TicketCategory


class Event(Base, TimestampMixin):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(300), index=True)
    entry_type: Mapped[str] = mapped_column(
        String(20), default=EntryType.EXCLUSIVE.value
    )
    category: Mapped[str] = mapped_column(
        String(30), default=TicketCategory.OTHER.value, index=True
    )
    category_code: Mapped[str | None] = mapped_column(String(60), nullable=True)
    starts_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sale_valid_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sale_valid_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    total_quota: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(String(60), default="48pedia")
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    sessions: Mapped[list["EventSession"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_events_starts_at_type", "starts_at", "entry_type"),)


class EventSession(Base, TimestampMixin):
    __tablename__ = "event_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True
    )
    member_id: Mapped[int | None] = mapped_column(
        ForeignKey("members.id", ondelete="SET NULL"), nullable=True, index=True
    )
    external_line_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    session_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    session_number: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    track_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ticket_category: Mapped[str] = mapped_column(
        String(30), default=TicketCategory.OTHER.value, index=True
    )
    starts_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    total_quota: Mapped[int | None] = mapped_column(Integer, nullable=True)

    event: Mapped["Event"] = relationship(back_populates="sessions")
    snapshots: Mapped[list["AvailabilitySnapshot"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "session_number",
            "member_id",
            "track_number",
            name="uq_session_event_member_track",
        ),
    )
