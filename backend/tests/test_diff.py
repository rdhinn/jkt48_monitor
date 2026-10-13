"""Tests for change detection."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.enums import AvailabilityStatus
from app.services.diff import CurrentState, PreviousState, detect_changes

SID = 1
PREFIX = "evTest"


def _detect(
    prev_status,
    prev_remaining,
    curr_status,
    curr_remaining,
    *,
    prev_start=None,
    curr_start=None,
):
    previous = (
        None
        if prev_status is None
        else PreviousState(
            status=prev_status,
            tickets_remaining=prev_remaining,
            starts_at=prev_start,
        )
    )
    current = CurrentState(
        status=curr_status,
        tickets_remaining=curr_remaining,
        starts_at=curr_start,
    )
    return detect_changes(
        SID, previous, current, event_key_prefix=PREFIX
    )


class TestDetection:
    def test_unknown_to_available_is_significant(self):
        changes = _detect("unknown", None, "available", None)
        assert len(changes) == 1
        assert changes[0].field == "status"
        assert changes[0].significant is True

    def test_sold_out_to_available_is_significant(self):
        changes = _detect("sold_out", 0, "available", 1)
        assert changes[0].significant is True

    def test_available_to_sold_out_is_significant(self):
        changes = _detect("available", 1, "sold_out", 0)
        assert changes[0].significant is True

    def test_unavailable_to_unknown_is_not_significant(self):
        changes = _detect("unavailable", None, "unknown", None)
        assert len(changes) == 1
        assert changes[0].significant is False

    def test_no_change_no_changes(self):
        changes = _detect("available", 5, "available", 5)
        assert changes == []

    def test_ticket_number_change(self):
        changes = _detect("available", 5, "available", 4)
        assert len(changes) == 1
        assert changes[0].field == "tickets_remaining"
        assert changes[0].previous == "5"
        assert changes[0].current == "4"
        assert changes[0].significant is True

    def test_new_event(self):
        changes = _detect(None, None, "available", 3)
        assert len(changes) == 1
        assert changes[0].field == "new_event"
        assert changes[0].significant is True

    def test_new_event_with_unknown_status_notified(self):
        changes = _detect(None, None, "unknown", None)
        assert changes[0].field == "new_event"
        assert changes[0].significant is False

    def test_schedule_change(self):
        start = datetime(2025, 1, 1, 12, tzinfo=timezone.utc)
        moved = start + timedelta(hours=1)
        changes = _detect(
            "available", 5, "available", 5, prev_start=start, curr_start=moved
        )
        fields = {c.field for c in changes}
        assert "schedule" in fields
        assert any(c.significant for c in changes if c.field == "schedule")

    def test_schedule_within_tolerance_ignored(self):
        start = datetime(2025, 1, 1, 12, tzinfo=timezone.utc)
        jitter = start + timedelta(seconds=30)
        changes = _detect(
            "available", 5, "available", 5, prev_start=start, curr_start=jitter
        )
        assert changes == []

    def test_status_and_count_changes_combined(self):
        changes = _detect("available", 2, "sold_out", 0)
        fields = {c.field for c in changes}
        assert {"status", "tickets_remaining"} <= fields

    def test_event_keys_unique_per_type(self):
        status_changes = _detect("unknown", None, "available", None)
        count_changes = _detect("available", 2, "available", 3)
        fields = {c.field for c in status_changes + count_changes}
        assert fields == {"status", "tickets_remaining"}
        keys = {c.event_key for c in status_changes + count_changes}
        assert len(keys) == 2