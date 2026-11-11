"""Small helpers for times of day (minutes since midnight), dates and weekdays."""

from __future__ import annotations

import re
from datetime import date, timedelta

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
WEEKDAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
MONTH_NAMES = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)

_TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_time(value: object) -> int:
    """Parse a 24-hour HH:MM string into minutes since midnight."""
    if not isinstance(value, str) or not _TIME_RE.match(value.strip()):
        raise ValueError(f"{value!r} is not a 24-hour time, use HH:MM such as 09:00")
    hours, minutes = value.strip().split(":")
    return int(hours) * 60 + int(minutes)


def fmt_time(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def parse_date(value: object) -> date:
    """Parse a YYYY-MM-DD string into a date."""
    if not isinstance(value, str) or not _DATE_RE.match(value.strip()):
        raise ValueError(f"{value!r} is not a date, use YYYY-MM-DD such as 2026-10-26")
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError(f"{value!r} is not a real calendar date") from None


def weekday_key(d: date) -> str:
    return WEEKDAYS[d.weekday()]


def weekday_name(d: date) -> str:
    return WEEKDAY_NAMES[d.weekday()]


def normalise_weekday(value: object) -> str:
    """Return the three-letter key for a weekday name such as 'Monday' or 'mon'."""
    if isinstance(value, str):
        text = value.strip().lower()
        for key, name in zip(WEEKDAYS, WEEKDAY_NAMES):
            if text in (key, name.lower()):
                return key
    raise ValueError(f"{value!r} is not a weekday, use mon, tue, wed, thu, fri, sat or sun")


def long_date(d: date) -> str:
    """For example 'Monday 26 October 2026'. Locale independent."""
    return f"{weekday_name(d)} {d.day} {MONTH_NAMES[d.month - 1]} {d.year}"


def short_date(d: date) -> str:
    """For example 'Mon 2026-10-26'."""
    return f"{WEEKDAY_NAMES[d.weekday()][:3]} {d.isoformat()}"


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def last_day_of_month(year: int, month: int) -> int:
    if month == 12:
        return 31
    return (date(year, month + 1, 1) - timedelta(days=1)).day


def add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1
