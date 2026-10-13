"""Structured-ish logging setup that never logs secrets."""
from __future__ import annotations

import logging
import sys

_REDACT_KEYS = ("apikey", "api_key", "authorization", "token", "password", "secret")


class RedactingFilter(logging.Filter):
    """Best-effort redaction of secrets from log messages."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D102
        try:
            message = record.getMessage()
        except Exception:  # pragma: no cover - defensive
            return True
        lowered = message.lower()
        for key in _REDACT_KEYS:
            if key in lowered:
                record.msg = "[redacted log line containing a secret-like key]"
                record.args = ()
                break
        return True


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    if root.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    handler.addFilter(RedactingFilter())
    root.addHandler(handler)
    root.setLevel(level.upper())


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
