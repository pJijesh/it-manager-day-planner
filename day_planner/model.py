"""Plain data classes for the profile and the task list."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Meeting:
    title: str
    start: int  # minutes since midnight
    end: int
    weekdays: tuple[str, ...] = ()  # recurring weekly on these weekdays
    on: date | None = None  # or a single date


@dataclass(frozen=True)
class Duty:
    """A recurring duty. Only the fields needed by the chosen cadence are set."""

    id: str
    title: str
    minutes: int
    cadence: str
    preferred_start: int | None = None
    weekdays: tuple[str, ...] = ()  # cadence "weekdays"
    weekday: str | None = None  # cadence "weekly" and nth weekday rules
    day: int | None = None  # day-number rule
    last_working_day: bool = False  # last-working-day rule
    nth: int | None = None  # nth weekday rule (1 to 5, or -1 for the last)
    months: tuple[int, ...] = ()  # cadence "quarterly"
    month: int | None = None  # cadence "annual"
    if_not_working: str = "next"  # "next" or "previous" working day
    notes: str = ""


@dataclass(frozen=True)
class Profile:
    name: str
    organisation: str
    hours: dict  # weekday key -> (start, end) in minutes; missing key = not a working day
    lunch: tuple[int, int] | None
    buffer_percent: float
    min_block_minutes: int
    buffer_block_minutes: int
    deep_window: tuple[int, int] | None
    meetings: tuple[Meeting, ...] = ()
    duties: tuple[Duty, ...] = ()
    bank_holidays: frozenset = field(default_factory=frozenset)


@dataclass(frozen=True)
class Task:
    id: str
    title: str
    category: str
    estimate_minutes: int
    due: date | None
    importance: int
    status: str
    blocked_by: tuple[str, ...] = ()
    earliest_start: date | None = None
    created: date | None = None
    completed: date | None = None
    actual_minutes: int | None = None
    line: int = 0
