"""Single source of the current time, so every timestamp is timezone-aware UTC."""

from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
