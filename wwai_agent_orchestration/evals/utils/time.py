"""Time helpers used by eval components."""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)

