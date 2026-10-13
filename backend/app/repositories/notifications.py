"""Notification subscription and log queries."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import NotificationLog, NotificationSubscription


async def list_subscriptions(
    db: AsyncSession, user_id: int | None = None
) -> list[NotificationSubscription]:
    stmt = select(NotificationSubscription).order_by(
        NotificationSubscription.created_at.desc()
    )
    if user_id is not None:
        stmt = stmt.where(NotificationSubscription.user_id == user_id)
    return list((await db.execute(stmt)).scalars().all())


async def enabled_subscriptions(db: AsyncSession) -> list[NotificationSubscription]:
    stmt = select(NotificationSubscription).where(
        NotificationSubscription.enabled.is_(True)
    )
    return list((await db.execute(stmt)).scalars().all())


async def get_subscription(
    db: AsyncSession, subscription_id: int
) -> NotificationSubscription | None:
    return await db.get(NotificationSubscription, subscription_id)


async def upsert_subscription(
    db: AsyncSession,
    user_id: int,
    *,
    telegram_chat_id: str | None,
    event_type: str,
    member_id: int | None,
    enabled: bool,
) -> NotificationSubscription:
    stmt = select(NotificationSubscription).where(
        NotificationSubscription.user_id == user_id,
        NotificationSubscription.event_type == event_type,
        NotificationSubscription.member_id == member_id,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        existing.telegram_chat_id = telegram_chat_id
        existing.enabled = enabled
        await db.flush()
        return existing
    sub = NotificationSubscription(
        user_id=user_id,
        telegram_chat_id=telegram_chat_id,
        event_type=event_type,
        member_id=member_id,
        enabled=enabled,
    )
    db.add(sub)
    await db.flush()
    return sub


async def delete_subscription(db: AsyncSession, subscription_id: int) -> None:
    sub = await db.get(NotificationSubscription, subscription_id)
    if sub:
        await db.delete(sub)
        await db.flush()


async def log_exists(db: AsyncSession, event_key: str) -> bool:
    stmt = select(NotificationLog.id).where(NotificationLog.event_key == event_key)
    return (await db.execute(stmt)).scalar_one_or_none() is not None


async def create_log(
    db: AsyncSession,
    *,
    subscription_id: int | None,
    event_key: str,
    message: str,
    delivery_status: str = "pending",
) -> NotificationLog:
    log = NotificationLog(
        subscription_id=subscription_id,
        event_key=event_key,
        message=message,
        delivery_status=delivery_status,
    )
    db.add(log)
    await db.flush()
    return log


async def list_logs(db: AsyncSession, limit: int = 50) -> list[NotificationLog]:
    stmt = (
        select(NotificationLog)
        .order_by(NotificationLog.attempted_at.desc())
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())


async def pending_logs(db: AsyncSession, limit: int = 50) -> list[NotificationLog]:
    stmt = (
        select(NotificationLog)
        .where(NotificationLog.delivery_status.in_(["pending", "retry"]))
        .order_by(NotificationLog.attempted_at.asc())
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())
