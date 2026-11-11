"""Week plan carry-over, flags and the weekly review."""

import json
from datetime import date

import pytest

from day_planner.errors import InputError
from day_planner.review import build_review
from day_planner.week import plan_week
from helpers import profile, tasks

MON = date(2026, 10, 26)


def short_week_profile(**kw):
    base = dict(working_hours={d: ["09:00", "13:00"] for d in ("mon", "tue", "wed", "thu", "fri")},
                lunch=None, buffer_percent=0)
    base.update(kw)
    return profile(**base)


def test_week_must_start_on_a_monday():
    with pytest.raises(InputError, match="2026-10-27 is a Tuesday.*2026-10-26"):
        plan_week(profile(), [], date(2026, 10, 27))


def test_long_task_carries_forward_and_unblocks_its_dependant():
    # Each day has 240 free minutes. A (300 minutes) takes 240 on Monday and 60 on Tuesday.
    t = tasks("A,Big,300,admin,,3,todo,,,\nB,After,30,admin,,3,todo,A,,")
    week = plan_week(short_week_profile(), t, MON)
    minutes = [r["task_minutes"] for r in week.rows]
    assert minutes[:3] == [240, 60, 30]
    assert [x["id"] for x in week.rows[2]["tasks"]] == ["B"]
    # On Tuesday A finishes, but B only becomes eligible the day after, and says it assumed A is done.
    assert [e["id"] for e in week.days[1].excluded] == ["B"]
    reason = week.days[2].task_blocks()[0].reason
    assert "assumes A" in reason and "2026-10-27" in reason
    assert week.not_scheduled == [] and week.excluded == []


def test_not_today_entries_say_when_the_task_is_planned_later():
    t = tasks("A,Big,300,admin,,3,todo,,,")
    week = plan_week(short_week_profile(), t, MON)
    entry = week.days[0].not_today[0]
    assert entry["planned_later"] == "2026-10-27" and entry["suggested_day"] == "2026-10-27"


def test_tasks_that_never_fit_are_listed_for_the_week():
    t = tasks("A,Huge,2000,admin,,3,todo,,,")  # the week has 5 x 240 = 1200 free minutes
    week = plan_week(short_week_profile(), t, MON)
    assert week.summary["task_minutes_planned"] == 1200
    assert week.not_scheduled[0]["id"] == "A" and week.not_scheduled[0]["minutes_left"] == 800


def test_overloaded_day_is_flagged():
    p = short_week_profile(
        fixed_meetings=[{"title": "Offsite", "weekday": "wed", "start": "09:00", "end": "13:00"}],
        recurring_duties=[{"title": "Check", "cadence": "daily", "minutes": 15}],
    )
    week = plan_week(p, [], MON)
    wed = week.rows[2]
    assert "OVERLOADED" in wed["flags"]  # 240 + 15 = 255 against 240
    assert wed["fixed_percent"] == 106
    assert week.summary["overloaded_days"] == ["Wednesday"]
    assert week.rows[0]["flags"] == []


def test_bank_holiday_in_the_week():
    week = plan_week(profile(bank_holidays=["2026-10-28"]), [], MON)
    assert week.rows[2]["flags"] == ["NOT A WORKING DAY"] and week.rows[2]["working_minutes"] == 0


def test_task_capacity_totals():
    week = plan_week(profile(), [], MON)
    # Each plain day: W = 420, buffer 125, so 295 left. Five days.
    assert week.summary["working_minutes"] == 2100
    assert week.summary["buffer_minutes"] == 625
    assert week.summary["task_capacity_minutes"] == 1475


def test_review_figures_by_hand():
    t = tasks(
        "A,Done with actual,60,admin,2026-10-27,3,done,,2026-10-27,75\n"
        "B,Done on estimate,45,admin,,3,done,,2026-10-28,\n"
        "C,Done last week,30,admin,,3,done,,2026-10-19,\n"
        "D,Overdue,30,admin,2026-10-20,3,todo,,,\n"
        "E,Due this week,30,admin,2026-10-29,3,todo,,,\n"
        "F,In progress later,30,admin,2026-11-20,3,in_progress,,,\n"
        "G,Due next week,30,admin,2026-11-03,3,todo,,,\n"
        "H,Waiting,30,admin,,3,waiting,,,\n"
        "I,Blocked,30,admin,,3,todo,E,,\n"
        "J,Done no date,30,admin,,3,done,,,",
        header="id,title,estimate_minutes,category,due,importance,status,blocked_by,completed,actual_minutes",
    )
    r = build_review(profile(), t, MON)
    assert r["capacity"]["working_minutes"] == 2100 and r["capacity"]["task_capacity_minutes"] == 1475
    assert [d["id"] for d in r["done"]] == ["A", "B"]
    assert [d["minutes"] for d in r["done"]] == [75, 45]
    assert [d["minutes_source"] for d in r["done"]] == ["actual", "estimate"]
    assert r["done_minutes"] == 120
    assert r["output_percent_of_task_capacity"] == 8  # 120 / 1475 = 8.1 percent
    assert r["done_without_completed_date"] == ["J"]
    assert [x["id"] for x in r["overdue"]] == ["D"] and r["overdue"][0]["days_late"] == 6
    assert [x["id"] for x in r["rolled_over"]] == ["E", "F"]
    assert [x["id"] for x in r["due_next_week"]] == ["G"]
    assert {x["id"]: x["waiting_for"] for x in r["waiting_or_blocked"]} == {"H": [], "I": ["E"]}


def test_review_requires_monday_and_serialises():
    with pytest.raises(InputError):
        build_review(profile(), [], date(2026, 10, 28))
    json.dumps(build_review(profile(), tasks("A,x,30,admin,,3,todo,,,"), MON))
