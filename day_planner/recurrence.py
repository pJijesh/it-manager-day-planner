"""When does a recurring duty fall? Pure date arithmetic, no clock and no network.

Definitions used throughout:

* A working day is a weekday that has working hours in the profile and is not
  listed in bank_holidays.
* "daily", "weekdays" and "weekly" duties simply do not run on a non-working day.
* Month-based duties (monthly_day, monthly_nth_weekday, quarterly, annual) work out a
  nominal date, then move it to the next or previous working day when the nominal date
  is not a working day (if_not_working, default "next").
* A day number larger than the month (31 in April, 30 or 29 in February) is clamped to
  the last day of that month. A leap day (29 February) therefore falls on 28 February
  in a common year.
"""

from __future__ import annotations

from datetime import date, timedelta

from .model import Duty, Profile
from .timeutil import (
    MONTH_NAMES, WEEKDAY_NAMES, WEEKDAYS, add_months, last_day_of_month, ordinal, weekday_key,
)


def is_working_day(profile: Profile, day: date) -> bool:
    return weekday_key(day) in profile.hours and day not in profile.bank_holidays


def last_working_day(profile: Profile, year: int, month: int) -> date:
    day = date(year, month, last_day_of_month(year, month))
    for _ in range(31):
        if is_working_day(profile, day):
            return day
        day -= timedelta(days=1)
    raise ValueError("no working day found in the month, check working_hours and bank_holidays")


def nth_weekday(year: int, month: int, weekday: str, nth: int) -> date | None:
    """The nth (1 to 5) or last (-1) given weekday of a month, or None if there is no such day."""
    target = WEEKDAYS.index(weekday)
    if nth == -1:
        day = date(year, month, last_day_of_month(year, month))
        while day.weekday() != target:
            day -= timedelta(days=1)
        return day
    first = date(year, month, 1)
    day = first + timedelta(days=(target - first.weekday()) % 7)
    day += timedelta(weeks=nth - 1)
    return day if day.month == month else None


def shift_to_working(profile: Profile, day: date, direction: str) -> date:
    step = timedelta(days=1 if direction == "next" else -1)
    for _ in range(60):
        if is_working_day(profile, day):
            return day
        day += step
    raise ValueError("no working day found near the date, check working_hours and bank_holidays")


def _nominal(duty: Duty, year: int, month: int) -> date | None:
    """The date the day rule points at in a month, before any working-day shift."""
    if duty.last_working_day:
        return None  # handled separately because it is already a working day
    if duty.day is not None:
        return date(year, month, min(duty.day, last_day_of_month(year, month)))
    return nth_weekday(year, month, duty.weekday, duty.nth)


def duty_dates_in_month(profile: Profile, duty: Duty, year: int, month: int) -> list[date]:
    """Dates (after working-day shifting) of a month-based duty for the nominal month given."""
    if duty.cadence == "quarterly" and month not in duty.months:
        return []
    if duty.cadence == "annual" and month != duty.month:
        return []
    if duty.cadence not in ("monthly_day", "monthly_last_working_day", "monthly_nth_weekday", "quarterly", "annual"):
        return []
    if duty.last_working_day:
        return [last_working_day(profile, year, month)]
    nominal = _nominal(duty, year, month)
    if nominal is None:
        return []
    return [shift_to_working(profile, nominal, duty.if_not_working)]


def occurs_on(profile: Profile, duty: Duty, day: date) -> bool:
    """True if the duty is due on the given date."""
    if not is_working_day(profile, day):
        return False
    if duty.cadence == "daily":
        return True
    if duty.cadence == "weekdays":
        return weekday_key(day) in duty.weekdays
    if duty.cadence == "weekly":
        return weekday_key(day) == duty.weekday
    # Month-based: a shifted date can cross a month boundary, so look at the neighbouring months too.
    for delta in (-1, 0, 1):
        year, month = add_months(day.year, day.month, delta)
        if day in duty_dates_in_month(profile, duty, year, month):
            return True
    return False


def describe_cadence(duty: Duty) -> str:
    """A plain-English description of when the duty runs."""
    if duty.cadence == "daily":
        return "every working day"
    if duty.cadence == "weekdays":
        return "every " + ", ".join(WEEKDAY_NAMES[WEEKDAYS.index(d)] for d in duty.weekdays)
    if duty.cadence == "weekly":
        return f"weekly on {WEEKDAY_NAMES[WEEKDAYS.index(duty.weekday)]}"
    rule = _describe_rule(duty)
    shift = "" if duty.last_working_day else f", moved to the {duty.if_not_working} working day if needed"
    if duty.cadence in ("monthly_day", "monthly_last_working_day", "monthly_nth_weekday"):
        return f"monthly, {rule}{shift}"
    if duty.cadence == "quarterly":
        months = ", ".join(MONTH_NAMES[m - 1][:3] for m in duty.months)
        return f"quarterly ({months}), {rule}{shift}"
    return f"annually in {MONTH_NAMES[duty.month - 1]}, {rule}{shift}"


def _describe_rule(duty: Duty) -> str:
    if duty.last_working_day:
        return "on the last working day"
    if duty.day is not None:
        return f"on the {ordinal(duty.day)}"
    which = "last" if duty.nth == -1 else ordinal(duty.nth)
    return f"on the {which} {WEEKDAY_NAMES[WEEKDAYS.index(duty.weekday)]}"
