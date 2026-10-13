"""Telegram long-polling worker for bot commands."""
from __future__ import annotations

import asyncio

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.services import telegram

logger = get_logger(__name__)


class TelegramWorker:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._offset: int | None = None

    async def start(self) -> None:
        if not (settings.telegram_configured and settings.telegram_polling_enabled):
            return
        if self._task is not None and not self._task.done():
            return
        self._stop.clear()
        await telegram.set_commands()
        self._task = asyncio.create_task(self._loop())
        logger.info("Telegram polling worker started")

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                updates = await telegram.get_updates(self._offset, timeout=20)
            except Exception:  # noqa: BLE001
                logger.exception("Telegram polling failed")
                updates = []
            for update in updates:
                self._offset = update.get("update_id", 0) + 1
                message = update.get("message") or update.get("edited_message") or {}
                text = message.get("text")
                chat_id = (message.get("chat") or {}).get("id")
                if not text or chat_id is None:
                    continue
                try:
                    async with SessionLocal() as db:
                        reply = await telegram.handle_command(db, str(chat_id), text)
                    if reply:
                        await telegram.send_message(str(chat_id), reply)
                except Exception:  # noqa: BLE001
                    logger.exception("Failed to handle Telegram command")
            if not updates:
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=1)
                except asyncio.TimeoutError:
                    pass


telegram_worker = TelegramWorker()
