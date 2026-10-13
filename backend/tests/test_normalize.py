"""Tests for pure normalization helpers."""
from __future__ import annotations

import pytest

from app.connectors.normalize import (
    compute_tickets_remaining,
    derive_status,
    normalize_category,
    normalize_entry_type,
    normalize_status,
    parse_int,
)
from app.models.enums import AvailabilityStatus, EntryType, TicketCategory


class TestParseInt:
    @pytest.mark.parametrize(
        "value,expected",
        [
            (5, 5),
            (0, 0),
            ("7", 7),
            ("1,234", 1234),
            ("15", 15),
            (True, None),
            (False, None),
            (-1, None),
            (2.5, None),
            (4.0, 4),
            (None, None),
            ("", None),
            ("abc", None),
            ("tickets: 3 left", 3),
        ],
    )
    def test_parse_int(self, value, expected):
        assert parse_int(value) == expected


class TestNormalizeCategory:
    @pytest.mark.parametrize(
        "code,title,expected",
        [
            ("VC", "Video Call", TicketCategory.VIDEO_CALL),
            ("VIDEO_CALL", None, TicketCategory.VIDEO_CALL),
            ("M&G", "Meet and Greet", TicketCategory.MEET_GREET),
            ("MG", None, TicketCategory.MEET_GREET),
            ("2S", "2-Shot", TicketCategory.TWO_SHOT),
            ("TWO_SHOT", "Two Shot", TicketCategory.TWO_SHOT),
            ("NONE", None, TicketCategory.OTHER),
            (None, "Handshake Event", TicketCategory.OTHER),
            ("VC", "2Shot Session", TicketCategory.TWO_SHOT),
        ],
    )
    def test_category(self, code, title, expected):
        assert normalize_category(code, title) == expected


class TestNormalizeStatus:
    def test_known(self):
        assert normalize_status("available") == AvailabilityStatus.AVAILABLE
        assert normalize_status("SOLDOUT") == AvailabilityStatus.SOLD_OUT
        assert normalize_status("belum dibuka") == AvailabilityStatus.NOT_OPEN
        assert normalize_status("dibatalkan") == AvailabilityStatus.CANCELLED
        assert normalize_status("on sale") == AvailabilityStatus.AVAILABLE

    def test_unknown_string_falls_back(self):
        assert normalize_status("weird-value") == AvailabilityStatus.UNKNOWN
        assert normalize_status("") == AvailabilityStatus.UNKNOWN
        assert normalize_status(None) == AvailabilityStatus.UNKNOWN


class TestDeriveStatus:
    def test_positive_remaining(self):
        assert (
            derive_status(tickets_remaining=5, sales_open=None)
            == AvailabilityStatus.AVAILABLE
        )

    def test_zero_remaining(self):
        assert (
            derive_status(tickets_remaining=0, sales_open=True)
            == AvailabilityStatus.SOLD_OUT
        )

    def test_none_remaining_and_sales_closed(self):
        assert (
            derive_status(tickets_remaining=None, sales_open=False)
            == AvailabilityStatus.NOT_OPEN
        )

    def test_none_remaining_and_open(self):
        # No count + open must NOT become sold_out
        assert (
            derive_status(tickets_remaining=None, sales_open=True)
            == AvailabilityStatus.UNKNOWN
        )

    def test_missing_data_never_sold_out(self):
        assert (
            derive_status(tickets_remaining=None, sales_open=None)
            == AvailabilityStatus.UNKNOWN
        )

    def test_cancelled_wins(self):
        assert (
            derive_status(
                tickets_remaining=9, sales_open=True, is_cancelled=True
            )
            == AvailabilityStatus.CANCELLED
        )


class TestComputeRemaining:
    def test_prefers_available_count(self):
        assert compute_tickets_remaining(40, 10, 100) == 40

    def test_derives_from_quota_and_sold(self):
        assert compute_tickets_remaining(None, 30, 100) == 70

    def test_never_negative(self):
        assert compute_tickets_remaining(None, 120, 100) == 0

    def test_missing(self):
        assert compute_tickets_remaining(None, None, None) is None


class TestEntryType:
    def test_map(self):
        assert normalize_entry_type("EXCLUSIVE") == EntryType.EXCLUSIVE
        assert normalize_entry_type("SHOW") == EntryType.SHOW
        assert normalize_entry_type("garbage") == EntryType.GENERAL
        assert normalize_entry_type(None) == EntryType.GENERAL