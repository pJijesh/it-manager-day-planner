"""Small builders so tests can state a profile and tasks in a few lines."""

from __future__ import annotations

import copy

from day_planner.profile import parse_profile
from day_planner.tasks import parse_tasks
from day_planner.timeutil import fmt_time

BASE = {
    "name": "Test Manager",
    "organisation": "Test Org",
    "working_hours": {d: ["09:00", "17:00"] for d in ("mon", "tue", "wed", "thu", "fri")},
    "lunch": {"start": "12:00", "end": "13:00"},
    "buffer_percent": 30,
    "min_block_minutes": 30,
    "buffer_block_minutes": 60,
}


def profile(**overrides):
    data = copy.deepcopy(BASE)
    data.update(overrides)
    return parse_profile(data)


def tasks(csv_body: str, header: str = "id,title,estimate_minutes,category,due,importance,status,blocked_by,earliest_start,created"):
    return parse_tasks(header + "\n" + csv_body.strip() + "\n")


def spans(plan, kind=None):
    """(start, end) as HH:MM strings for the blocks of a kind, in order."""
    return [(fmt_time(b.start), fmt_time(b.end)) for b in plan.blocks if kind is None or b.kind == kind]
