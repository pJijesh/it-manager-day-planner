"""Input validation gives readable messages and reports every problem at once."""

import copy
import json

import pytest

from day_planner.errors import InputError
from day_planner.profile import load_profile, parse_profile
from day_planner.tasks import load_tasks, parse_tasks
from helpers import BASE


def problems_for(**changes):
    data = copy.deepcopy(BASE)
    data.update(changes)
    with pytest.raises(InputError) as exc:
        parse_profile(data)
    return exc.value.problems


def task_problems(text):
    with pytest.raises(InputError) as exc:
        parse_tasks(text)
    return exc.value.problems


# ---------------------------------------------------------------- profile

def test_bad_time_format_names_the_field_and_the_fix():
    hours = dict(BASE["working_hours"], mon=["9am", "17:00"])
    msg = problems_for(working_hours=hours)[0]
    assert "working_hours.mon" in msg and "'9am' is not a 24-hour time, use HH:MM such as 09:00" in msg


def test_impossible_time_is_rejected():
    hours = dict(BASE["working_hours"], mon=["09:00", "25:00"])
    assert "25:00" in problems_for(working_hours=hours)[0]


def test_end_before_start_is_rejected():
    hours = dict(BASE["working_hours"], mon=["17:00", "09:00"])
    assert "end 09:00 must be after start 17:00" in problems_for(working_hours=hours)[0]


def test_unknown_weekday_and_missing_hours():
    assert "not a weekday" in problems_for(working_hours={"funday": ["09:00", "17:00"]})[0]
    assert "at least one weekday" in problems_for(working_hours={"mon": None})[0]


def test_bad_lunch_and_numbers():
    assert "lunch" in problems_for(lunch={"start": "13:00", "end": "12:00"})[0]
    assert "buffer_percent" in problems_for(buffer_percent=120)[0]
    assert "min_block_minutes" in problems_for(min_block_minutes=2)[0]
    assert "bank_holidays[0]" in problems_for(bank_holidays=["26/12/2026"])[0]


def test_overlapping_fixed_meetings_are_rejected_with_both_names():
    msgs = problems_for(fixed_meetings=[
        {"title": "Stand-up", "weekday": "mon", "start": "09:00", "end": "09:30"},
        {"title": "Vendor call", "weekday": "mon", "start": "09:15", "end": "10:00"},
    ])
    assert len(msgs) == 1
    assert "overlap on Monday" in msgs[0] and "Stand-up" in msgs[0] and "Vendor call" in msgs[0]


def test_dated_meeting_overlapping_a_weekly_one_is_rejected():
    msgs = problems_for(fixed_meetings=[
        {"title": "Weekly", "weekday": "mon", "start": "09:00", "end": "10:00"},
        {"title": "One-off", "date": "2026-10-26", "start": "09:30", "end": "10:30"},
    ])
    assert "overlap on 2026-10-26" in msgs[0]


def test_meetings_on_different_days_or_back_to_back_are_fine():
    parse_profile({**BASE, "fixed_meetings": [
        {"title": "A", "weekday": "mon", "start": "09:00", "end": "10:00"},
        {"title": "B", "weekday": "tue", "start": "09:00", "end": "10:00"},
        {"title": "C", "weekday": "mon", "start": "10:00", "end": "11:00"},
        {"title": "D", "date": "2026-10-27", "start": "11:00", "end": "12:00"},
    ]})


def test_meeting_needs_exactly_one_day_selector():
    msgs = problems_for(fixed_meetings=[{"title": "X", "start": "09:00", "end": "10:00"}])
    assert "exactly one of weekday, weekdays or date" in msgs[0]


def test_unknown_profile_field_is_a_typo_guard():
    msg = problems_for(working_hrs={})[0]
    assert "working_hrs" in msg and "unknown field" in msg


def test_underscore_fields_are_ignored():
    parse_profile({**BASE, "_comment": "hello"})


def test_duty_validation():
    msgs = problems_for(recurring_duties=[
        {"title": "A", "cadence": "fortnightly", "minutes": 10},
        {"title": "B", "cadence": "weekly", "minutes": 10},
        {"title": "C", "cadence": "monthly_day", "day": 40, "minutes": 10},
        {"title": "D", "cadence": "monthly_nth_weekday", "nth": 6, "weekday": "mon", "minutes": 10},
        {"title": "E", "cadence": "annual", "day": 3, "minutes": 10},
        {"title": "F", "cadence": "daily", "minutes": 0},
        {"title": "G", "cadence": "daily", "minutes": 10, "preferred_start": "8am"},
    ])
    text = "\n".join(msgs)
    assert "'fortnightly' is not one of" in text
    assert "cadence weekly needs weekday" in text
    assert "day 40 must be a whole number from 1 to 31" in text
    assert "nth 6 must be" in text
    assert "annual needs month" in text
    assert "minutes 0" in text
    assert "preferred_start" in text and "'8am'" in text
    assert len(msgs) == 7  # every problem reported in one go


def test_duplicate_duty_ids():
    msgs = problems_for(recurring_duties=[
        {"id": "x", "title": "A", "cadence": "daily", "minutes": 5},
        {"id": "x", "title": "B", "cadence": "daily", "minutes": 5},
    ])
    assert "used twice" in msgs[0]


def test_load_profile_errors(tmp_path):
    with pytest.raises(InputError, match="not found"):
        load_profile(tmp_path / "missing.json")
    bad = tmp_path / "p.json"
    bad.write_text('{"name": ', encoding="utf-8")
    with pytest.raises(InputError, match=r"not valid JSON \(line 1, column"):
        load_profile(bad)
    bad.write_text("[]", encoding="utf-8")
    with pytest.raises(InputError, match="JSON object"):
        load_profile(bad)
    bad.write_text(json.dumps(BASE), encoding="utf-8")
    assert load_profile(bad).name == "Test Manager"


# ---------------------------------------------------------------- tasks

HEADER = "id,title,estimate_minutes,importance,status,blocked_by,due,earliest_start\n"


def test_unknown_blocked_by_id():
    msgs = task_problems(HEADER + "A,One,30,3,todo,Z9,,\n")
    assert msgs == ["tasks.csv line 2, blocked_by: 'Z9' is not a task id in this file"]


def test_task_blocked_by_itself():
    assert "blocked by itself" in task_problems(HEADER + "A,One,30,3,todo,A,,\n")[0]


def test_circular_blocking_prints_the_chain():
    msgs = task_problems(HEADER + "A,One,30,3,todo,C,,\nB,Two,30,3,todo,A,,\nC,Three,30,3,todo,B,,\n")
    assert len(msgs) == 1
    assert "circular blocking: A -> C -> B -> A" in msgs[0]
    assert "none can start" in msgs[0]


def test_two_task_cycle_is_reported_once():
    msgs = task_problems(HEADER + "A,One,30,3,todo,B,,\nB,Two,30,3,todo,A,,\n")
    assert len([m for m in msgs if "circular" in m]) == 1


def test_a_chain_without_a_cycle_is_fine():
    parse_tasks(HEADER + "A,One,30,3,todo,B,,\nB,Two,30,3,todo,C,,\nC,Three,30,3,todo,,,\n")


def test_row_level_problems_are_collected_with_line_numbers():
    msgs = task_problems(
        HEADER
        + "A,One,0,3,todo,,,\n"
        + "B,Two,30,9,todo,,,\n"
        + "C,Three,30,3,started,,,\n"
        + "D,Four,30,3,todo,,tomorrow,\n"
        + "A,Dup,30,3,todo,,,\n"
        + ",NoId,30,3,todo,,,\n"
        + "F,,30,3,todo,,,\n"
        + "G,Seven,abc,3,todo,,,\n"
        + "H,Eight,30,3,todo,,2026-02-30,\n"
    )
    text = "\n".join(msgs)
    assert "line 2, estimate_minutes: '0'" in text
    assert "line 3, importance: '9' must be a whole number from 1 to 5" in text
    assert "line 4, status: 'started' is not one of: todo, in_progress, waiting, done, cancelled" in text
    assert "line 5, due: 'tomorrow' is not a date, use YYYY-MM-DD" in text
    assert "line 6, id: 'A' is already used on line 2" in text
    assert "line 7, id: is empty" in text
    assert "line 8, title: is empty" in text
    assert "line 9, estimate_minutes: 'abc'" in text
    assert "line 10, due: '2026-02-30' is not a real calendar date" in text
    assert len(msgs) == 9


def test_missing_required_columns_and_empty_input():
    msgs = task_problems("id,title\nA,One\n")
    assert "missing required column(s): estimate_minutes" in msgs[0]
    assert "empty" in task_problems("")[0]
    assert "no tasks found" in task_problems("id,title,estimate_minutes\n")[0]


def test_defaults_and_flexible_blocked_by_separators():
    tasks = parse_tasks("id,title,estimate_minutes,blocked_by\nA,One,30,\nB,Two,30,\nC,Three,30,A; B\nD,Four,30,\"A,B\"\n")
    assert tasks[2].blocked_by == ("A", "B") and tasks[3].blocked_by == ("A", "B")
    assert (tasks[0].category, tasks[0].importance, tasks[0].status) == ("general", 3, "todo")


def test_bom_and_load_tasks_errors(tmp_path):
    path = tmp_path / "t.csv"
    path.write_bytes(b"\xef\xbb\xbfid,title,estimate_minutes\nA,One,30\n")
    assert load_tasks(path)[0].id == "A"
    with pytest.raises(InputError, match="not found"):
        load_tasks(tmp_path / "nope.csv")
