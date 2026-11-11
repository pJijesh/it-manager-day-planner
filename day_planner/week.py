"""Plan Monday to Friday by running the day planner for each day and carrying work forward."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from .errors import InputError
from .model import Profile, Task
from .scheduler import DayPlan, plan_day
from .tasks import CLEARED_STATUSES
from .timeutil import weekday_name


@dataclass
class WeekPlan:
    start: date
    days: list[DayPlan]
    rows: list[dict] = field(default_factory=list)
    not_scheduled: list[dict] = field(default_factory=list)
    excluded: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    @property
    def end(self) -> date:
        return self.start + timedelta(days=4)


def require_monday(day: date, option: str) -> None:
    if day.weekday() != 0:
        raise InputError(
            f"{option} {day.isoformat()} is a {weekday_name(day)}. A week starts on a Monday, "
            f"for example {(day - timedelta(days=day.weekday())).isoformat()}"
        )


def plan_week(profile: Profile, tasks: list[Task], start: date, buffer_percent: float | None = None) -> WeekPlan:
    require_monday(start, "week start")
    remaining = {t.id: t.estimate_minutes for t in tasks if t.status not in CLEARED_STATUSES}
    original = dict(remaining)
    assumed_done: dict[str, date] = {}
    days: list[DayPlan] = []
    for offset in range(5):
        day = start + timedelta(days=offset)
        plan = plan_day(profile, tasks, day, buffer_percent, remaining, assumed_done)
        for block in plan.task_blocks():
            remaining[block.task_id] -= block.minutes
        for task_id, left in remaining.items():
            if left == 0 and task_id not in assumed_done:
                assumed_done[task_id] = day
        days.append(plan)

    week = WeekPlan(start=start, days=days)

    # Tell each "not today" entry when the task is planned later in the week, if it is.
    first_block: dict[str, list[date]] = {}
    for plan in days:
        for block in plan.task_blocks():
            first_block.setdefault(block.task_id, []).append(plan.date)
    for plan in days:
        for entry in plan.not_today:
            later = [d for d in first_block.get(entry["id"], []) if d > plan.date]
            entry["planned_later"] = later[0].isoformat() if later else None
            if later:
                entry["suggested_day"] = later[0].isoformat()

    week.rows = [_row(plan, profile) for plan in days]

    seen_eligible: set[str] = set()
    for plan in days:
        seen_eligible.update(b.task_id for b in plan.task_blocks())
        seen_eligible.update(n["id"] for n in plan.not_today)
    by_id = {t.id: t for t in tasks}
    for task_id in sorted(seen_eligible, key=lambda i: (by_id[i].line, i)):
        left = remaining.get(task_id, 0)
        if left > 0:
            last = next((n for plan in reversed(days) for n in plan.not_today if n["id"] == task_id), None)
            week.not_scheduled.append({
                "id": task_id, "title": by_id[task_id].title, "minutes_left": left,
                "minutes_needed": original[task_id],
                "reason": f"{left} of {original[task_id]} minutes could not be placed in the week: "
                          "capacity was used up by meetings, duties, the buffer and higher-scoring tasks.",
                "due": by_id[task_id].due.isoformat() if by_id[task_id].due else None,
                "suggested_day": last["suggested_day"] if last else None,
            })
    latest: dict[str, dict] = {}
    for plan in days:  # a later day's wording replaces an earlier one
        for entry in plan.excluded:
            latest[entry["id"]] = entry
    week.excluded = [latest[i] for i in sorted(latest, key=lambda i: (by_id[i].line, i)) if i not in seen_eligible]

    working = sum(r["working_minutes"] for r in week.rows)
    task_capacity = sum(r["task_capacity_minutes"] for r in week.rows)
    planned = sum(r["task_minutes"] for r in week.rows)
    week.summary = {
        "working_minutes": working,
        "meeting_minutes": sum(r["meeting_minutes"] for r in week.rows),
        "duty_minutes": sum(r["duty_minutes"] for r in week.rows),
        "buffer_minutes": sum(r["buffer_minutes"] for r in week.rows),
        "task_capacity_minutes": task_capacity,
        "task_minutes_planned": planned,
        "tasks_not_scheduled": len(week.not_scheduled),
        "overloaded_days": [r["weekday"] for r in week.rows if "OVERLOADED" in r["flags"]],
        "flagged_days": [r["weekday"] for r in week.rows if r["flags"]],
    }
    return week


def _row(plan: DayPlan, profile: Profile) -> dict:
    cap = plan.capacity
    working = cap["working_minutes"]
    flags: list[str] = []
    if not plan.working_day:
        flags.append("NOT A WORKING DAY")
    else:
        commitments = cap["fixed_commitment_minutes"]
        room = working - commitments - cap["buffer_target_minutes"]
        if commitments > working:
            flags.append("OVERLOADED")
        elif room <= 0:
            flags.append("NO TASK TIME")
        elif room < 2 * profile.min_block_minutes:
            flags.append("TIGHT")
        unplaced_due = [n for n in plan.not_today if n.get("note") and not n.get("planned_later")]
        if unplaced_due:
            flags.append(f"{len(unplaced_due)} DUE OR OVERDUE NOT PLACED")
        if plan.unplaced_duties:
            flags.append("DUTY NOT PLACED")
    fixed_pct = round(100 * cap["fixed_commitment_minutes"] / working) if working else 0
    return {
        "date": plan.date.isoformat(),
        "weekday": weekday_name(plan.date),
        "working_day": plan.working_day,
        "working_minutes": working,
        "meeting_minutes": cap["meeting_minutes"],
        "duty_minutes": cap["duty_minutes"],
        "buffer_minutes": cap["buffer_minutes"],
        "task_minutes": cap["task_minutes_planned"],
        "free_minutes": cap["free_minutes"],
        "task_capacity_minutes": cap["task_capacity_minutes"],
        "fixed_percent": fixed_pct,
        "flags": flags,
        "tasks": [{"id": b.task_id, "title": b.title, "minutes": b.minutes, "part": b.part}
                  for b in plan.task_blocks()],
    }
