"""Telegram Bot API client and command handlers."""
from __future__ import annotations

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.enums import STATUS_LABELS
from app.repositories import availability as availability_repo
from app.repositories import favorites as fav_repo
from app.repositories import members as member_repo
from app.repositories import notifications as notif_repo

logger = get_logger(__name__)

HELP_TEXT = (
    "JKT48 Availability Monitor\n\n"
    "Perintah tersedia:\n"
    "/start - daftar chat & petunjuk\n"
    "/status - ringkasan status terbaru\n"
    "/members - daftar member\n"
    "/availability - ringkasan ketersediaan\n"
    "/favorite - lihat member favorit\n"
    "/history - perubahan terbaru\n"
    "/help - daftar perintah\n"
)

_DEFAULT_USER_ID = 1


class TelegramError(Exception):
    pass


async def send_message(
    chat_id: str, text: str, *, token: str | None = None
) -> tuple[bool, str | None]:
    """Send a Telegram message. Returns (ok, error)."""
    bot_token = (token if token is not None else settings.telegram_bot_token).strip()
    if not bot_token:
        return False, "TELEGRAM_BOT_TOKEN not configured"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
            )
        if response.status_code == 200:
            return True, None
        return False, f"HTTP {response.status_code}"
    except httpx.HTTPError as exc:  # pragma: no cover - network
        return False, str(exc)


async def get_updates(offset: int | None = None, *, timeout: int = 25) -> list[dict]:
    bot_token = settings.telegram_bot_token.strip()
    if not bot_token:
        return []
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    params = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    try:
        async with httpx.AsyncClient(timeout=timeout + 10) as client:
            response = await client.get(url, params=params)
        if response.status_code != 200:
            logger.warning("getUpdates failed: HTTP %s", response.status_code)
            return []
        return response.json().get("result", [])
    except httpx.HTTPError as exc:  # pragma: no cover
        logger.warning("getUpdates error: %s", exc)
        return []


async def set_commands() -> None:
    bot_token = settings.telegram_bot_token.strip()
    if not bot_token:
        return
    commands = [
        {"command": "start", "description": "Daftar & petunjuk"},
        {"command": "status", "description": "Ringkasan status"},
        {"command": "availability", "description": "Ketersediaan tiket"},
        {"command": "members", "description": "Daftar member"},
        {"command": "favorite", "description": "Member favorit"},
        {"command": "history", "description": "Perubahan terbaru"},
        {"command": "help", "description": "Bantuan"},
    ]
    url = f"https://api.telegram.org/bot{bot_token}/setMyCommands"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            await client.post(url, json={"commands": commands})
    except httpx.HTTPError:  # pragma: no cover
        pass


async def handle_command(db: AsyncSession, chat_id: str, text: str) -> str | None:
    """Handle a bot command. Returns the reply text, or None to stay silent."""
    if not text or not text.startswith("/"):
        return None
    command = text.split()[0].split("@")[0].lower()

    if command == "/start":
        await notif_repo.upsert_subscription(
            db,
            _DEFAULT_USER_ID,
            telegram_chat_id=chat_id,
            event_type="all",
            member_id=None,
            enabled=True,
        )
        await db.commit()
        return (
            "Terdaftar untuk notifikasi JKT48 Availability Monitor.\n\n" + HELP_TEXT
        )

    if command in ("/help",):
        return HELP_TEXT

    if command == "/status":
        counts = await availability_repo.status_counts(db)
        if not counts:
            return "Belum ada data ketersediaan. Konfigurasikan JKT48_API_KEY lalu jalankan refresh."
        lines = ["Ringkasan status sesi:"]
        for status, label in STATUS_LABELS.items():
            if status.value in counts:
                lines.append(f"- {label}: {counts[status.value]}")
        return "\n".join(lines)

    if command == "/availability":
        rows, total = await availability_repo.list_availability(db, limit=10)
        if not rows:
            return "Belum ada data ketersediaan."
        lines = [f"Ketersediaan terbaru (menampilkan {len(rows)} dari {total}):"]
        for row in rows:
            member = row.get("member_name") or row.get("event_name")
            remaining = row.get("tickets_remaining")
            remaining_text = "jumlah tidak tersedia" if remaining is None else str(remaining)
            status = STATUS_LABELS.get(
                _as_status(row.get("status")), row.get("status") or "unknown"
            )
            lines.append(f"- {member} | sesi {row.get('session_number')} | {status} | sisa {remaining_text}")
        return "\n".join(lines)

    if command == "/members":
        members, total = await member_repo.list_members(db, limit=30)
        if not members:
            return "Belum ada data member."
        lines = [f"Member aktif ({total} total, menampilkan {len(members)}):"]
        lines += [f"- {m.name} ({m.team_code or '-'})" for m in members]
        return "\n".join(lines)

    if command == "/favorite":
        favs = await fav_repo.list_for_user(db, _DEFAULT_USER_ID)
        if not favs:
            return "Belum ada member favorit."
        return "Member favorit:\n" + "\n".join(f"- {m.name}" for m in favs)

    if command == "/history":
        rows, total = await availability_repo.history(db, limit=10)
        if not rows:
            return "Belum ada histori perubahan."
        lines = [f"Perubahan terbaru ({total} total):"]
        for row in rows:
            remaining = row.get("tickets_remaining")
            remaining_text = "n/a" if remaining is None else str(remaining)
            lines.append(
                f"- {row.get('member_name') or row.get('event_name')} | "
                f"{row.get('status')} | sisa {remaining_text} | {row.get('observed_at')}"
            )
        return "\n".join(lines)

    return "Perintah tidak dikenal. Kirim /help untuk daftar perintah."


def _as_status(value: str | None):
    from app.models.enums import AvailabilityStatus

    if value is None:
        return None
    try:
        return AvailabilityStatus(value)
    except ValueError:
        return None
