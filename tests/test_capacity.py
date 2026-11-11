"""Capacity and buffer arithmetic, checked against values worked out by hand."""

from datetime import date
from fractions import Fraction

import pytest

from day_planner.scheduler import plan_day, round_buffer
from helpers import profile, spans, tasks

MON = date(2026, 10, 26)


@pytest.mark.parametrize(
    "working, percent, expected, exact",
    [
        (420, 30, 125, Fraction(126)),  # 126 is closer to 125 than to 130
        (495, 30, 150, Fraction(297, 2)),  # 148.5 rounds to 150
        (435, 30, 130, Fraction(261, 2)),  # 130.5 rounds to 130
        (450, 12.5, 55, Fraction(225, 4)),  # 56.25 rounds to 55
        (100, 2.5, 5, Fraction(5, 2)),  # 2.5 is exactly half of 5 and rounds up
        (420, 0, 0, Fraction(0)),
        (240, 30, 70, Fraction(72)),
    ],
)
def test_round_buffer(working, percent, expected, exact):
    assert round_buffer(working, percent) == (expected, exact)


def test_empty_day_capacity_and_buffer_blocks():
    # 09:00 to 17:00 is 480 minutes, lunch 60, so W = 420. Buffer 30% = 126, rounded to 125.
    plan = plan_day(profile(), [], MON)
    cap = plan.capacity
    assert cap["working_minutes"] == 420
    assert cap["buffer_target_minutes"] == 125
    assert cap["buffer_minutes"] == 125
    assert cap["meeting_minutes"] == 0 and cap["duty_minutes"] == 0
    assert cap["free_minutes"] == 295
    # Reserve 125 in m = 3 parts of 45, 40, 40. Pool is 09:00-12:00 and 13:00-17:00 (n = 420).
    # Part centres are at offsets 70, 210 and 350, so the first part goes to the morning gap
    # (45 minutes from its end) and the other two to the afternoon gap (80 minutes from its end).
    assert spans(plan, "buffer") == [("11:15", "12:00"), ("15:40", "17:00")]


def test_meeting_and_duty_arithmetic():
    # W = 420. Meeting 10:00 to 11:00 is 60. A 30 minute duty at 09:00. Free = 420 - 60 - 30 = 330.
    p = profile(
        fixed_meetings=[{"title": "Meet", "weekday": "mon", "start": "10:00", "end": "11:00"}],
        recurring_duties=[{"title": "Check", "cadence": "daily", "minutes": 30, "preferred_start": "09:00"}],
    )
    plan = plan_day(p, [], MON)
    cap = plan.capacity
    assert (cap["working_minutes"], cap["meeting_minutes"], cap["duty_minutes"]) == (420, 60, 30)
    assert cap["buffer_target_minutes"] == 125
    # Free gaps: 09:30-10:00 (30), 11:00-12:00 (60), 13:00-17:00 (240). Parts of 45, 40, 40 sit at
    # pool offsets 55, 165, 275. The 60 minute gap cannot give 45 without leaving 15 (under the 30
    # minute minimum), so it gives all 60 and the last part shrinks by 15 to 65.
    assert spans(plan, "buffer") == [("11:00", "12:00"), ("15:55", "17:00")]
    assert cap["buffer_minutes"] == 125
    assert cap["task_capacity_minutes"] == 330 - 125 == 205
    assert spans(plan, "duty") == [("09:00", "09:30")]
    assert spans(plan, "meeting") == [("10:00", "11:00")]
    assert spans(plan, "lunch") == [("12:00", "13:00")]


def test_capacity_identity_holds_with_tasks():
    p = profile(
        fixed_meetings=[{"title": "Meet", "weekday": "mon", "start": "10:00", "end": "11:00"}],
        recurring_duties=[{"title": "Check", "cadence": "daily", "minutes": 30, "preferred_start": "09:00"}],
    )
    t = tasks("A,Alpha,90,admin,,3,todo,,,\nB,Beta,45,admin,,3,todo,,,\nC,Gamma,200,admin,,3,todo,,,")
    plan = plan_day(p, t, MON)
    cap = plan.capacity
    assert cap["working_minutes"] == (cap["meeting_minutes"] + cap["duty_minutes"] + cap["buffer_minutes"]
                                      + cap["task_minutes_planned"] + cap["free_minutes"])
    assert sum(b.minutes for b in plan.blocks if b.kind != "lunch") == cap["working_minutes"]


def test_blocks_never_overlap_and_stay_inside_working_hours():
    p = profile(deep_work_window={"start": "09:00", "end": "11:00"},
                fixed_meetings=[{"title": "M", "weekday": "mon", "start": "10:00", "end": "10:45"}])
    t = tasks("\n".join(f"T{i},Task {i},{40 + 5 * i},{'deep' if i % 3 == 0 else 'admin'},,{1 + i % 5},todo,,," for i in range(12)))
    plan = plan_day(p, t, MON)
    blocks = sorted(plan.blocks, key=lambda b: b.start)
    assert blocks[0].start >= 9 * 60 and blocks[-1].end <= 17 * 60
    for a, b in zip(blocks, blocks[1:]):
        assert a.end <= b.start


def test_meeting_overlapping_lunch_shortens_lunch_without_reducing_capacity():
    p = profile(fixed_meetings=[{"title": "Lunch and learn", "weekday": "mon", "start": "12:30", "end": "13:30"}])
    plan = plan_day(p, [], MON)
    assert spans(plan, "lunch") == [("12:00", "12:30")]
    assert plan.capacity["working_minutes"] == 420
    assert plan.capacity["meeting_minutes"] == 30  # only the 30 minutes after lunch count
    assert any("overlaps lunch" in w["message"] for w in plan.warnings)


def test_meeting_outside_hours_is_ignored_with_a_warning():
    p = profile(fixed_meetings=[{"title": "Early call", "weekday": "mon", "start": "07:00", "end": "08:00"}])
    plan = plan_day(p, [], MON)
    assert plan.capacity["meeting_minutes"] == 0
    assert any("outside working hours" in w["message"] for w in plan.warnings)


def test_buffer_override_changes_the_target_and_adds_a_note():
    plan = plan_day(profile(), [], MON, buffer_percent=50)
    assert plan.capacity["buffer_target_minutes"] == 210  # 50% of 420
    assert plan.capacity["buffer_minutes"] == 210
    assert any("50%" in w["message"] and w["level"] == "info" for w in plan.warnings)


def test_zero_buffer_gives_no_buffer_blocks():
    plan = plan_day(profile(buffer_percent=0), [], MON)
    assert spans(plan, "buffer") == []
    assert plan.capacity["free_minutes"] == 420


def test_short_gaps_count_toward_the_buffer():
    # Meetings leave a 20 minute gap at 10:00 to 10:20, shorter than the 30 minute minimum block.
    p = profile(
        buffer_percent=10,
        fixed_meetings=[
            {"title": "A", "weekday": "mon", "start": "09:00", "end": "10:00"},
            {"title": "B", "weekday": "mon", "start": "10:20", "end": "12:00"},
        ],
    )
    plan = plan_day(p, [], MON)
    assert ("10:00", "10:20") in spans(plan, "buffer")
    # Target is 10% of 420 = 42, rounded to 40. The 20 minute gap supplies 20 of it, so only 20 more is reserved.
    assert plan.capacity["buffer_target_minutes"] == 40
    assert plan.capacity["buffer_minutes"] == 40


def test_deep_window_is_kept_free_of_buffer_when_possible():
    p = profile(deep_work_window={"start": "09:00", "end": "11:00"})
    plan = plan_day(p, [], MON)
    for start, end in spans(plan, "buffer"):
        assert start >= "11:00", (start, end)
    assert plan.capacity["buffer_minutes"] == 125


def test_non_working_day_gives_a_note_and_no_blocks():
    plan = plan_day(profile(), [], date(2026, 10, 24))  # a Saturday
    assert not plan.working_day and plan.blocks == []
    assert "not a working day" in plan.warnings[0]["message"]
    plan = plan_day(profile(bank_holidays=["2026-10-26"]), [], MON)
    assert not plan.working_day and "bank_holidays" in plan.warnings[0]["message"]
