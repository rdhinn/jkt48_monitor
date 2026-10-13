"""Favorites and Telegram notification models."""
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
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utcnow


class Favorite(Base):
    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    member_id: Mapped[int] = mapped_column(
        ForeignKey("members.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    __table_args__ = (
        UniqueConstraint("user_id", "member_id", name="uq_favorite_user_member"),
    )


class NotificationSubscription(Base):
    __tablename__ = "notification_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    telegram_chat_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_type: Mapped[str] = mapped_column(String(30), default="all")
    member_id: Mapped[int | None] = mapped_column(
        ForeignKey("members.id", ondelete="CASCADE"), nullable=True, index=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int | None] = mapped_column(
        ForeignKey("notification_subscriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    message: Mapped[str] = mapped_column(Text)
    delivery_status: Mapped[str] = mapped_column(String(30), default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_notif_status_attempted", "delivery_status", "attempted_at"),
    )
