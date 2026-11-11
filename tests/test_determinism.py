"""The same inputs always give the same output, whatever the order of the task rows."""

import random
from datetime import date
from pathlib import Path

from day_planner import render_html, render_json, render_md
from day_planner.profile import load_profile
from day_planner.scheduler import plan_day
from day_planner.tasks import load_tasks
from day_planner.week import plan_week

EX = Path(__file__).resolve().parent.parent / "examples"
DAY = date(2026, 10, 26)


def test_repeated_runs_are_identical():
    p, t = load_profile(EX / "profile.json"), load_tasks(EX / "tasks.csv")
    first = render_json.dumps(render_json.day_to_dict(plan_day(p, t, DAY)))
    for _ in range(3):
        assert render_json.dumps(render_json.day_to_dict(plan_day(p, t, DAY))) == first
    assert render_html.render_day(plan_day(p, t, DAY)) == render_html.render_day(plan_day(p, t, DAY))
    assert render_md.render_day(plan_day(p, t, DAY)) == render_md.render_day(plan_day(p, t, DAY))


def test_row_order_of_the_task_file_does_not_change_the_plan():
    p, t = load_profile(EX / "profile.json"), load_tasks(EX / "tasks.csv")
    base = plan_day(p, t, DAY)
    shuffled = list(t)
    random.Random(7).shuffle(shuffled)
    other = plan_day(p, shuffled, DAY)
    assert [(b.start, b.end, b.kind, b.title) for b in base.blocks] == [(b.start, b.end, b.kind, b.title) for b in other.blocks]
    assert [n["id"] for n in base.not_today] == [n["id"] for n in other.not_today]
    assert base.capacity == other.capacity


def test_week_is_deterministic():
    p, t = load_profile(EX / "profile.json"), load_tasks(EX / "tasks.csv")
    a = render_json.dumps(render_json.week_to_dict(plan_week(p, t, DAY), True))
    b = render_json.dumps(render_json.week_to_dict(plan_week(p, t, DAY), True))
    assert a == b


def test_no_timestamps_or_machine_paths_in_outputs():
    for path in (EX / "output").iterdir():
        text = path.read_text(encoding="utf-8")
        assert "/home/" not in text and "/tmp/" not in text, path.name
