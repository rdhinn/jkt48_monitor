"""Notification dispatch with per-subscription deduplication."""
from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.db.base import utcnow
from app.models import NotificationSubscription
from app.repositories import notifications as notif_repo
from app.services import telegram
from app.services.diff import Change

logger = get_logger(__name__)


def _subscription_matches(
    sub: NotificationSubscription, row: dict, change: Change
) -> bool:
    if not sub.telegram_chat_id:
        return False
    if sub.event_type and sub.event_type != "all":
        if row.get("ticket_category") != sub.event_type:
            return False
    if sub.member_id is not None and row.get("member_id") != sub.member_id:
        return False
    return True


def format_change_message(change: Change, row: dict) -> str:
    member = row.get("member_name") or row.get("event_name") or "Sesi"
    category = row.get("ticket_category") or "-"
    session_no = row.get("session_number")
    if change.field == "new_event":
        title = "Event baru"
        body = f"Status awal: {change.current}"
    elif change.field == "status":
        title = "Perubahan status tiket"
        body = f"{change.previous} -> {change.current}"
    elif change.field == "tickets_remaining":
        title = "Perubahan jumlah tiket"
        body = f"sisa {change.previous} -> {change.current}"
    elif change.field == "schedule":
        title = "Perubahan jadwal"
        body = f"{change.previous} -> {change.current}"
    else:
        title = "Perubahan"
        body = f"{change.previous} -> {change.current}"

    lines = [
        f"<b>{title}</b>",
        f"Member: {member}",
        f"Kategori: {category}",
        f"Sesi: {session_no if session_no is not None else '-'}",
        f"Event: {row.get('event_name') or '-'}",
        body,
    ]
    return "\n".join(lines)


async def notify_changes(
    db: AsyncSession, changes: list[Change], rows_by_session: dict[int, dict]
) -> int:
    significant = [c for c in changes if c.significant]
    if not significant:
        return 0
    if not settings.telegram_configured:
        return 0

    subscriptions = await notif_repo.enabled_subscriptions(db)
    if not subscriptions:
        return 0

    sent = 0
    for change in significant:
        row = rows_by_session.get(change.session_id, {})
        for sub in subscriptions:
            if not _subscription_matches(sub, row, change):
                continue
            log_key = f"sub{sub.id}:{change.event_key}"
            if await notif_repo.log_exists(db, log_key):
                continue
            message = format_change_message(change, row)
            log = await notif_repo.create_log(
                db,
                subscription_id=sub.id,
                event_key=log_key,
                message=message,
                delivery_status="pending",
            )
            delivered = await _deliver_with_retry(log, sub.telegram_chat_id, message)
            if delivered:
                sent += 1
            await db.flush()
    await db.commit()
    return sent


async def _deliver_with_retry(log, chat_id: str, message: str) -> bool:
    max_retries = max(1, settings.telegram_notify_max_retries)
    delay = 1.0
    for attempt in range(1, max_retries + 1):
        log.attempt_count = attempt
        ok, error = await telegram.send_message(chat_id, message)
        if ok:
            log.delivery_status = "sent"
            log.delivered_at = utcnow()
            log.error_message = None
            return True
        log.delivery_status = "retry" if attempt < max_retries else "failed"
        log.error_message = error
        if attempt < max_retries:
            await asyncio.sleep(delay)
            delay *= 2
    return False


async def retry_pending(db: AsyncSession) -> int:
    """Retry previously failed notifications (bounded)."""
    if not settings.telegram_configured:
        return 0
    pending = await notif_repo.pending_logs(db, limit=25)
    sent = 0
    subscriptions = {
        sub.id: sub for sub in await notif_repo.list_subscriptions(db)
    }
    for log in pending:
        sub = subscriptions.get(log.subscription_id or -1)
        if not sub or not sub.telegram_chat_id:
            log.delivery_status = "failed"
            log.error_message = "subscription missing"
            continue
        ok, error = await telegram.send_message(sub.telegram_chat_id, log.message)
        log.attempt_count += 1
        if ok:
            log.delivery_status = "sent"
            log.delivered_at = utcnow()
            sent += 1
        else:
            log.delivery_status = "failed" if log.attempt_count >= 5 else "retry"
            log.error_message = error
    await db.commit()
    return sent
