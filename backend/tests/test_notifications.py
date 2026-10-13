"""Tests for notification deduplication and delivery."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.models import (
    NotificationLog,
    NotificationSubscription,
)
from app.models.enums import AvailabilityStatus, TicketCategory
from app.repositories import notifications as notif_repo
from app.services.diff import Change
from app.services import notifier


def _make_change(status="seller"):
    return Change(
        session_id=1,
        field="status",
        previous="sold_out",
        current=AvailabilityStatus.AVAILABLE.value,
        significant=True,
        event_key="evTest:status:1:sold_out->available",
    )


def _row():
    return {
        "session_id": 1,
        "event_id": 1,
        "event_name": "Video Call Event",
        "member_id": 1,
        "member_name": "Fiony Alveria",
        "ticket_category": TicketCategory.VIDEO_CALL.value,
        "session_number": 1,
        "status": "available",
    }


class TestDeduplication:
    async def test_same_change_sent_once(self, db_session, telegram_enabled, monkeypatch):
        await notif_repo.upsert_subscription(
            db_session,
            user_id=1,
            telegram_chat_id="1234",
            event_type="all",
            member_id=None,
            enabled=True,
        )
        await db_session.commit()

        sends = {"n": 0}

        async def fake_send(chat_id, text, *, token=None):
            sends["n"] += 1
            return True, None

        monkeypatch.setattr(notifier.telegram, "send_message", fake_send)

        rows = {1: _row()}
        await notifier.notify_changes(db_session, [_make_change()], rows)
        # identical change, must be deduplicated per-subscription
        await notifier.notify_changes(db_session, [_make_change()], rows)

        assert sends["n"] == 1
        logs = (await notifier.notif_repo.list_logs(db_session, limit=20))
        assert len(logs) == 1
        assert logs[0].delivery_status == "sent"

    async def test_different_changes_send_twice(self, db_session, telegram_enabled, monkeypatch):
        await notif_repo.upsert_subscription(
            db_session,
            user_id=1,
            telegram_chat_id="1234",
            event_type="all",
            member_id=None,
            enabled=True,
        )
        await db_session.commit()
        sends = {"n": 0}

        async def fake_send(chat_id, text, *, token=None):
            sends["n"] += 1
            return True, None

        monkeypatch.setattr(notifier.telegram, "send_message", fake_send)

        rows = {1: _row()}
        change_a = _make_change()
        change_b = Change(
            session_id=1,
            field="status",
            previous="sold_out",
            current="available",
            significant=True,
            event_key="evTest:status:1:OTHER->available",
        )
        await notifier.notify_changes(db_session, [change_a], rows)
        await notifier.notify_changes(db_session, [change_b], rows)
        assert sends["n"] == 2

    async def test_non_significant_not_sent(self, db_session, telegram_enabled, monkeypatch):
        await notif_repo.upsert_subscription(
            db_session,
            user_id=1,
            telegram_chat_id="1234",
            event_type="all",
            member_id=None,
            enabled=True,
        )
        await db_session.commit()
        sends = {"n": 0}

        async def fake_send(chat_id, text, *, token=None):
            sends["n"] += 1
            return True, None

        monkeypatch.setattr(notifier.telegram, "send_message", fake_send)
        change = Change(
            session_id=1,
            field="status",
            previous="unavailable",
            current="unknown",
            significant=False,
            event_key="evTest:status:1:unavailable->unknown",
        )
        await notifier.notify_changes(db_session, [change], {1: _row()})
        assert sends["n"] == 0

    async def test_member_scoped_subscription_filters(self, db_session, telegram_enabled, monkeypatch):
        await notif_repo.upsert_subscription(
            db_session,
            user_id=1,
            telegram_chat_id="1234",
            event_type="video_call",
            member_id=99,  # different member
            enabled=True,
        )
        await db_session.commit()
        sends = {"n": 0}

        async def fake_send(chat_id, text, *, token=None):
            sends["n"] += 1
            return True, None

        monkeypatch.setattr(notifier.telegram, "send_message", fake_send)
        await notifier.notify_changes(db_session, [_make_change()], {1: _row()})
        assert sends["n"] == 0

    async def test_failed_delivery_retries_then_fails(self, db_session, telegram_enabled, monkeypatch):
        await notif_repo.upsert_subscription(
            db_session,
            user_id=1,
            telegram_chat_id="1234",
            event_type="all",
            member_id=None,
            enabled=True,
        )
        await db_session.commit()
        attempts = {"n": 0}

        async def failing_send(chat_id, text, *, token=None):
            attempts["n"] += 1
            return False, "boom"

        monkeypatch.setattr(notifier.telegram, "send_message", failing_send)
        await notifier.notify_changes(db_session, [_make_change()], {1: _row()})
        logs = (await notifier.notif_repo.list_logs(db_session, limit=20))
        assert len(logs) == 1
        assert logs[0].delivery_status == "failed"
        assert logs[0].attempt_count == 2
        assert attempts["n"] == 2