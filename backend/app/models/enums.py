"""Enumerations shared across models, connectors and services."""
from __future__ import annotations

from enum import Enum


class AvailabilityStatus(str, Enum):
    AVAILABLE = "available"
    SOLD_OUT = "sold_out"
    NOT_OPEN = "not_open"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"
    CANCELLED = "cancelled"


class EntryType(str, Enum):
    SHOW = "SHOW"
    EVENT = "EVENT"
    EXCLUSIVE = "EXCLUSIVE"
    BIRTHDAY = "BIRTHDAY"
    GENERAL = "GENERAL"


class TicketCategory(str, Enum):
    VIDEO_CALL = "video_call"
    MEET_GREET = "meet_greet"
    TWO_SHOT = "two_shot"
    OTHER = "other"


STATUS_LABELS = {
    AvailabilityStatus.AVAILABLE: "Tersedia",
    AvailabilityStatus.SOLD_OUT: "Habis",
    AvailabilityStatus.NOT_OPEN: "Belum dibuka",
    AvailabilityStatus.UNKNOWN: "Tidak diketahui",
    AvailabilityStatus.UNAVAILABLE: "Sumber tidak tersedia",
    AvailabilityStatus.CANCELLED: "Dibatalkan",
}

CATEGORY_LABELS = {
    TicketCategory.VIDEO_CALL: "Video Call",
    TicketCategory.MEET_GREET: "Meet & Greet",
    TicketCategory.TWO_SHOT: "2-Shot",
    TicketCategory.OTHER: "Lainnya",
}
