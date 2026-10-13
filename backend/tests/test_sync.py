"""Tests for synchronization with a fake connector."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select

from app.connectors.base import BaseConnector
from app.connectors.types import NormalizedEvent, NormalizedMember, NormalizedSession
from app.models import AvailabilitySnapshot, Member
from app.models.enums import EntryType, TicketCategory
from app.services.sync import perform_sync
from app.repositories import availability as availability_repo


class FakeConnector(BaseConnector):
    name = "fake"
    base_url = "https://fake.test"
    supported_features = ["members", "events", "ticket_stock"]

    def __init__(self, session) -> None:
        super().__init__()
        self.session = session

    @property
    def configured(self) -> bool:
        return True

    async def fetch_members(self) -> list[NormalizedMember]:
        return [
            NormalizedMember(
                external_id="FIONY",
                name="Fiony Alveria",
                nickname="Fiony",
                team_code="K3",
            )
        ]

    async def fetch_events(self) -> list[NormalizedEvent]:
        return [
            NormalizedEvent(
                external_id="SH999",
                name="Theater Show",
                entry_type=EntryType.SHOW,
                starts_at=datetime(2025, 7, 2, 12, tzinfo=timezone.utc),
            )
        ]

    async def fetch_ticket_sales(self) -> list[NormalizedEvent]:
        event = NormalizedEvent(
            external_id="EX1",
            name="Video Call Event",
            entry_type=EntryType.EXCLUSIVE,
            category=TicketCategory.VIDEO_CALL,
            category_code="VC",
            starts_at=datetime(2025, 7, 2, 12, tzinfo=timezone.utc),
        )
        event.sessions = self._sessions()
        return [event]

    def _sessions(self) -> list[NormalizedSession]:
        return [
            NormalizedSession(
                external_line_id="line1",
                session_number=1,
                track_number=1,
                member_external_id="FIONY",
                member_name="Fiony Alveria",
                ticket_category=TicketCategory.VIDEO_CALL,
                starts_at=datetime(2025, 7, 2, 12, tzinfo=timezone.utc),
                status=self.session["status"],
                tickets_remaining=self.session["remaining"],
            )
        ]

    async def fetch_event_sales(self, external_id: str) -> NormalizedEvent | None:
        return (await self.fetch_ticket_sales())[0]

    async def health(self) -> bool:
        return True


async def _run(db, conn):
    return await perform_sync(db, conn)


class TestSync:
    async def test_full_sync_creates_rows_and_changes(self, db_session):
        conn = FakeConnector({"status": "available", "remaining": 5})
        result = await _run(db_session, conn)

        assert result.members_synced == 1
        assert result.events_synced == 2
        assert result.sessions_synced == 1
        assert result.success is True

        members = (await db_session.execute(select(Member))).scalars().all()
        assert len(members) == 1

        rows, total = await availability_repo.list_availability(db_session, limit=10)
        assert total == 1
        assert rows[0]["status"] == "available"
        assert rows[0]["tickets_remaining"] == 5
        assert rows[0]["member_name"] == "Fiony Alveria"
        assert rows[0]["ticket_category"] == "video_call"

        fields = {c.field for c in result.changes}
        assert "new_event" in fields
        snap_count = (
            await db_session.execute(
                select(func.count()).select_from(AvailabilitySnapshot)
            )
        ).scalar_one()
        assert snap_count == 1

    async def test_unchanged_sync_creates_no_changes(self, db_session):
        conn = FakeConnector({"status": "available", "remaining": 5})
        first = await _run(db_session, conn)
        second = await _run(db_session, conn)
        assert second.snapshots_written == 1
        assert second.changes == []

    async def test_status_change_detected_across_runs(self, db_session):
        conn = FakeConnector({"status": "available", "remaining": 5})
        await _run(db_session, conn)
        conn.session = {"status": "sold_out", "remaining": 0}
        result = await _run(db_session, conn)
        fields = {c.field for c in result.changes}
        assert {"status", "tickets_remaining"} <= fields
        significant = [c for c in result.changes if c.significant]
        assert len(significant) >= 1

    async def test_history_written(self, db_session):
        conn = FakeConnector({"status": "available", "remaining": 3})
        await _run(db_session, conn)
        conn.session = {"status": "available", "remaining": 2}
        await _run(db_session, conn)

        rows, total = await availability_repo.history(db_session, limit=20)
        assert total == 2
        assert rows[0]["tickets_remaining"] == 2
        assert rows[1]["tickets_remaining"] == 3