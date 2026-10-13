"""Telegram notification subscription endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.deps import DbSession, ResolvedUser
from app.core.config import settings
from app.repositories import notifications as notif_repo
from app.schemas.dashboard import (
    NotificationLogOut,
    NotificationSubscriptionIn,
    NotificationSubscriptionOut,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(db: DbSession, user: ResolvedUser) -> dict:
    subscriptions = await notif_repo.list_subscriptions(db, user.id)
    logs = await notif_repo.list_logs(db, limit=30)
    return {
        "telegram_configured": settings.telegram_configured,
        "subscriptions": [
            NotificationSubscriptionOut.model_validate(s) for s in subscriptions
        ],
        "logs": [NotificationLogOut.model_validate(log) for log in logs],
    }


@router.put("", response_model=NotificationSubscriptionOut)
async def upsert_notification(
    payload: NotificationSubscriptionIn, db: DbSession, user: ResolvedUser
) -> NotificationSubscriptionOut:
    if payload.event_type not in ("all", "video_call", "meet_greet", "two_shot"):
        raise HTTPException(status_code=422, detail="event_type tidak valid.")
    sub = await notif_repo.upsert_subscription(
        db,
        user.id,
        telegram_chat_id=payload.telegram_chat_id,
        event_type=payload.event_type,
        member_id=payload.member_id,
        enabled=payload.enabled,
    )
    await db.commit()
    return NotificationSubscriptionOut.model_validate(sub)


@router.delete("/{subscription_id}")
async def delete_notification(
    subscription_id: int, db: DbSession, user: ResolvedUser
) -> dict:
    sub = await notif_repo.get_subscription(db, subscription_id)
    if sub is None or sub.user_id != user.id:
        raise HTTPException(status_code=404, detail="Langganan tidak ditemukan.")
    await notif_repo.delete_subscription(db, subscription_id)
    await db.commit()
    return {"detail": "Langganan dihapus."}
