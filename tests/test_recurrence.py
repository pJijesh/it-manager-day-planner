"""Recurrence rules: last working day, nth weekday, month end, leap day, holidays."""

import copy
from datetime import date

from day_planner.recurrence import (
    describe_cadence, duty_dates_in_month, is_working_day, last_working_day, nth_weekday, occurs_on,
)
from day_planner.profile import parse_profile
from helpers import BASE


def make(holidays=(), **fields):
    """A profile with one recurring duty. Returns (profile, duty)."""
    data = copy.deepcopy(BASE)
    data["bank_holidays"] = list(holidays)
    data["recurring_duties"] = [{"title": "Duty", "minutes": 15, **fields}]
    prof = parse_profile(data)
    return prof, prof.duties[0]


def test_working_day_skips_weekends_and_holidays():
    prof, _ = make(holidays=["2026-12-25"], cadence="daily")
    assert is_working_day(prof, date(2026, 12, 24))
    assert not is_working_day(prof, date(2026, 12, 25))  # holiday
    assert not is_working_day(prof, date(2026, 12, 26))  # Saturday


def test_last_working_day_friday_and_weekend_month_ends():
    prof, _ = make(cadence="daily")
    assert last_working_day(prof, 2026, 10) == date(2026, 10, 30)  # 31 Oct 2026 is a Saturday
    assert last_working_day(prof, 2026, 11) == date(2026, 11, 30)  # a Monday
    assert last_working_day(prof, 2027, 1) == date(2027, 1, 29)  # 31 Jan 2027 is a Sunday


def test_last_working_day_skips_a_holiday():
    prof, _ = make(holidays=["2026-12-31"], cadence="daily")
    assert last_working_day(prof, 2026, 12) == date(2026, 12, 30)
    prof, _ = make(holidays=["2026-10-30"], cadence="daily")
    assert last_working_day(prof, 2026, 10) == date(2026, 10, 29)


def test_monthly_last_working_day_occurs_only_once():
    prof, d = make(cadence="monthly_last_working_day")
    hits = [date(2026, 10, n) for n in range(1, 32) if occurs_on(prof, d, date(2026, 10, n))]
    assert hits == [date(2026, 10, 30)]


def test_nth_weekday_helper():
    assert nth_weekday(2026, 10, "wed", 2) == date(2026, 10, 14)
    assert nth_weekday(2026, 10, "fri", -1) == date(2026, 10, 30)
    assert nth_weekday(2026, 10, "thu", 5) == date(2026, 10, 29)
    assert nth_weekday(2026, 10, "wed", 5) is None  # only four Wednesdays in October 2026
    assert nth_weekday(2026, 11, "mon", 1) == date(2026, 11, 2)


def test_monthly_nth_weekday_occurrence():
    prof, d = make(cadence="monthly_nth_weekday", nth=2, weekday="wed")
    assert occurs_on(prof, d, date(2026, 10, 14))
    assert not occurs_on(prof, d, date(2026, 10, 7))
    assert not occurs_on(prof, d, date(2026, 10, 21))


def test_fifth_weekday_missing_month_gives_no_occurrence():
    prof, d = make(cadence="monthly_nth_weekday", nth=5, weekday="wed")
    assert duty_dates_in_month(prof, d, 2026, 10) == []
    assert duty_dates_in_month(prof, d, 2026, 12) == [date(2026, 12, 30)]  # Wednesdays: 2, 9, 16, 23, 30


def test_day_number_clamped_to_month_end():
    prof, d = make(cadence="monthly_day", day=31)
    assert duty_dates_in_month(prof, d, 2026, 11) == [date(2026, 11, 30)]  # 30 days, and a Monday
    assert duty_dates_in_month(prof, d, 2026, 4) == [date(2026, 4, 30)]


def test_day_31_in_february_moves_by_the_chosen_direction():
    prof, d = make(cadence="monthly_day", day=31)  # 28 Feb 2027 is a Sunday
    assert duty_dates_in_month(prof, d, 2027, 2) == [date(2027, 3, 1)]
    prof, d = make(cadence="monthly_day", day=31, if_not_working="previous")
    assert duty_dates_in_month(prof, d, 2027, 2) == [date(2027, 2, 26)]


def test_leap_day_annual_duty():
    prof, d = make(cadence="annual", month=2, day=29)
    assert duty_dates_in_month(prof, d, 2028, 2) == [date(2028, 2, 29)]  # leap year, a Tuesday
    assert occurs_on(prof, d, date(2028, 2, 29))
    # 2026 is a common year: day 29 becomes 28 February, a Saturday, so it moves to Monday 2 March
    assert duty_dates_in_month(prof, d, 2026, 2) == [date(2026, 3, 2)]
    assert occurs_on(prof, d, date(2026, 3, 2))
    assert not occurs_on(prof, d, date(2026, 2, 27))


def test_holiday_shifts_a_monthly_duty_to_the_next_working_day():
    holidays = ["2026-12-25", "2026-12-28"]
    prof, d = make(holidays=holidays, cadence="monthly_day", day=25)
    assert duty_dates_in_month(prof, d, 2026, 12) == [date(2026, 12, 29)]
    prof, d = make(holidays=holidays, cadence="monthly_day", day=25, if_not_working="previous")
    assert duty_dates_in_month(prof, d, 2026, 12) == [date(2026, 12, 24)]


def test_shift_can_cross_a_month_boundary_and_is_still_found():
    prof, d = make(cadence="monthly_day", day=1, if_not_working="previous")  # 1 Nov 2026 is a Sunday
    assert occurs_on(prof, d, date(2026, 10, 30))
    assert not occurs_on(prof, d, date(2026, 11, 2))
    prof, d = make(cadence="monthly_day", day=1)
    assert occurs_on(prof, d, date(2026, 11, 2))
    assert not occurs_on(prof, d, date(2026, 10, 30))


def test_daily_weekdays_and_weekly_do_not_run_on_holidays():
    holidays = ["2026-10-26"]
    prof, daily = make(holidays=holidays, cadence="daily")
    assert not occurs_on(prof, daily, date(2026, 10, 26))
    assert occurs_on(prof, daily, date(2026, 10, 27))
    prof, weekly = make(holidays=holidays, cadence="weekly", weekday="mon")
    assert not occurs_on(prof, weekly, date(2026, 10, 26))
    assert occurs_on(prof, weekly, date(2026, 11, 2))
    prof, wd = make(holidays=holidays, cadence="weekdays", weekdays=["tue", "thu"])
    assert occurs_on(prof, wd, date(2026, 10, 27)) and occurs_on(prof, wd, date(2026, 10, 29))
    assert not occurs_on(prof, wd, date(2026, 10, 28))


def test_quarterly_and_annual():
    prof, q = make(cadence="quarterly", day=5)
    assert occurs_on(prof, q, date(2026, 10, 5))  # a Monday
    assert not occurs_on(prof, q, date(2026, 11, 5))
    assert occurs_on(prof, q, date(2027, 1, 5))
    prof, q = make(cadence="quarterly", months=[3, 9], last_working_day=True)
    assert occurs_on(prof, q, date(2026, 9, 30))
    assert not occurs_on(prof, q, date(2026, 10, 30))
    prof, a = make(cadence="annual", month=11, day=3)
    assert occurs_on(prof, a, date(2026, 11, 3))
    assert not occurs_on(prof, a, date(2026, 12, 3))


def test_describe_cadence_is_plain_english():
    _, d = make(cadence="monthly_nth_weekday", nth=2, weekday="wed")
    assert describe_cadence(d).startswith("monthly, on the 2nd Wednesday")
    _, d = make(cadence="monthly_last_working_day")
    assert describe_cadence(d) == "monthly, on the last working day"
    _, d = make(cadence="weekly", weekday="mon")
    assert describe_cadence(d) == "weekly on Monday"
