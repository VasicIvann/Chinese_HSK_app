"""The user's time zone, sent by the browser in the `X-Timezone` header.

Days ("today", streaks, heatmap cells) must follow the user's clock, not the
server's (Render runs in UTC): a review at 07:00 in Shanghai is 23:00 UTC the
day before. Timestamps stay stored in naive UTC; only day bucketing uses this.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import Header

UTC = ZoneInfo("UTC")


def parse_timezone(name: str | None) -> ZoneInfo:
    """IANA name (e.g. "Europe/Paris") -> ZoneInfo; anything invalid falls back to UTC."""
    if not name:
        return UTC
    name = name.strip()
    if not name or len(name) > 64:
        return UTC
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return UTC


def get_user_timezone(x_timezone: str | None = Header(default=None)) -> ZoneInfo:
    """FastAPI dependency."""
    return parse_timezone(x_timezone)


def local_date(naive_utc: datetime, tz: ZoneInfo) -> date:
    """Calendar day, in `tz`, of a naive-UTC timestamp from the database."""
    return naive_utc.replace(tzinfo=timezone.utc).astimezone(tz).date()


def local_today(tz: ZoneInfo, now_utc: datetime | None = None) -> date:
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.astimezone(tz).date()


__all__ = ["UTC", "get_user_timezone", "local_date", "local_today", "parse_timezone"]
