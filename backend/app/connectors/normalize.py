"""Normalization helpers shared by connectors.

These functions are intentionally pure so they can be unit tested without
network access.
"""
from __future__ import annotations

import re
from typing import Any

from app.models.enums import AvailabilityStatus, EntryType, TicketCategory

_VIDEO_TOKENS = ("video call", "video_call", "videocall", "vc")
_MEET_TOKENS = ("meet and greet", "meet & greet", "meet_greet", "meet greet", "m&g", "mg", "meet")
_TWO_SHOT_TOKENS = ("2-shot", "2 shot", "2shot", "two shot", "two-shot", "2s")


def parse_int(value: Any) -> int | None:
    """Parse a non-negative integer or return None.

    Rejects booleans, floats that are not integral, and negatives.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, float):
        if value.is_integer() and value >= 0:
            return int(value)
        return None
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "").replace(".", "")
        if not cleaned:
            return None
        match = re.search(r"\d+", cleaned)
        if not match:
            return None
        return int(match.group(0))
    return None


def normalize_category(category_code: str | None, title: str | None = None) -> TicketCategory:
    haystack = f"{category_code or ''} {title or ''}".lower().replace("&amp;", "&")
    tokens = re.split(r"[\s_\-/]+", haystack)
    for token in _TWO_SHOT_TOKENS:
        if token in haystack:
            return TicketCategory.TWO_SHOT
    for token in _MEET_TOKENS:
        if token in tokens or token in haystack:
            return TicketCategory.MEET_GREET
    for token in _VIDEO_TOKENS:
        if token in tokens or token in haystack:
            return TicketCategory.VIDEO_CALL
    return TicketCategory.OTHER


def normalize_entry_type(value: str | None) -> EntryType:
    if not value:
        return EntryType.GENERAL
    upper = value.strip().upper()
    for entry in EntryType:
        if entry.value == upper:
            return entry
    return EntryType.GENERAL


def normalize_status(value: str | None) -> AvailabilityStatus:
    """Map a source-provided status string to a canonical status."""
    if not value:
        return AvailabilityStatus.UNKNOWN
    lowered = value.strip().lower().replace(" ", "_").replace("-", "_")
    mapping = {
        "available": AvailabilityStatus.AVAILABLE,
        "open": AvailabilityStatus.AVAILABLE,
        "on_sale": AvailabilityStatus.AVAILABLE,
        "tersedia": AvailabilityStatus.AVAILABLE,
        "sold_out": AvailabilityStatus.SOLD_OUT,
        "soldout": AvailabilityStatus.SOLD_OUT,
        "habis": AvailabilityStatus.SOLD_OUT,
        "empty": AvailabilityStatus.SOLD_OUT,
        "not_open": AvailabilityStatus.NOT_OPEN,
        "not_started": AvailabilityStatus.NOT_OPEN,
        "coming_soon": AvailabilityStatus.NOT_OPEN,
        "belum_dibuka": AvailabilityStatus.NOT_OPEN,
        "cancelled": AvailabilityStatus.CANCELLED,
        "canceled": AvailabilityStatus.CANCELLED,
        "dibatalkan": AvailabilityStatus.CANCELLED,
        "unavailable": AvailabilityStatus.UNAVAILABLE,
        "unknown": AvailabilityStatus.UNKNOWN,
    }
    return mapping.get(lowered, AvailabilityStatus.UNKNOWN)


def derive_status(
    *,
    tickets_remaining: int | None,
    sales_open: bool | None,
    is_cancelled: bool | None = None,
) -> AvailabilityStatus:
    """Derive a status strictly from valid data.

    Never turns a missing/error value into ``sold_out``.
    """
    if is_cancelled:
        return AvailabilityStatus.CANCELLED
    if tickets_remaining is not None:
        return (
            AvailabilityStatus.AVAILABLE
            if tickets_remaining > 0
            else AvailabilityStatus.SOLD_OUT
        )
    if sales_open is False:
        return AvailabilityStatus.NOT_OPEN
    return AvailabilityStatus.UNKNOWN


def compute_tickets_remaining(
    available_count: int | None, sold_count: int | None, total_quota: int | None
) -> int | None:
    """Prefer the explicit available count; otherwise derive from quota - sold."""
    if available_count is not None:
        return available_count
    if total_quota is not None and sold_count is not None:
        remaining = total_quota - sold_count
        return remaining if remaining >= 0 else 0
    return None
