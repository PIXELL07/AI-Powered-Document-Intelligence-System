"""
datetime.utcnow() is deprecated as of Python 3.12 (scheduled for removal),
because it returns a naive datetime that's easy to accidentally compare
against or mix with timezone-aware datetimes. The replacement,
datetime.now(timezone.utc), returns an *aware* datetime instead.

This app stores naive UTC datetimes throughout (DB columns, JWT expiry,
anomaly due-date comparisons) and mixing aware/naive would raise
TypeError at comparison time, so utcnow() here deliberately strips the
tzinfo back off to preserve the exact previous behavior while avoiding
the deprecation warning -- a drop-in replacement, not a behavior change.
"""
from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
