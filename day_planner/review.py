"""Weekly review: what was done, what rolled over, what is overdue, and capacity against output.

The tool has no time tracking. "Actual" output is the actual_minutes recorded for each task
completed in the week, or the estimate where no actual is recorded (marked as such).
"""

from __future__ import annotations

from datetime import date, timedelta

from .model import Profile, Task
from .scheduler import plan_day
from .scoring import natural_key
from .tasks import CLEARED_STATUSES
from .timeutil import weekday_name
from .week import require_monday


def build_review(profile: Profile, tasks: list[Task], week_start: date, buffer_percent: float | None = None) -> dict:
    require_monday(week_start, "week start")
    days = [week_start + timedelta(days=i) for i in range(5)]
    friday = days[-1]

    capacity = {"working_minutes": 0, "meeting_minutes": 0, "duty_minutes": 0, "buffer_minutes": 0, "task_capacity_minutes": 0}
    for day in days:
        cap = plan_day(profile, [], day, buffer_percent).capacity
        for key in capacity:
            capacity[key] += cap[key]

    by_id = {t.id: t for t in tasks}

    def row(task: Task, **extra) -> dict:
        return {"id": task.id, "title": task.title, "category": task.category, "importance": task.importance,
                "due": task.due.isoformat() if task.due else None, "status": task.status,
                "estimate_minutes": task.estimate_minutes, **extra}

    done = sorted((t for t in tasks if t.status == "done" and t.completed and week_start <= t.completed <= friday + timedelta(days=2)),
                  key=lambda t: (t.completed, natural_key(t.id)))
    done_rows = []
    for t in done:
        minutes = t.actual_minutes if t.actual_minutes is not None else t.estimate_minutes
        done_rows.append(row(t, completed=t.completed.isoformat(), minutes=minutes,
                             minutes_source="actual" if t.actual_minutes is not None else "estimate"))
    done_minutes = sum(r["minutes"] for r in done_rows)
    done_undated = sorted(t.id for t in tasks if t.status == "done" and not t.completed)

    open_tasks = [t for t in tasks if t.status not in CLEARED_STATUSES]
    open_sorted = sorted(open_tasks, key=lambda t: (t.due or date.max, -t.importance, natural_key(t.id)))
    overdue = [row(t, days_late=(week_start - t.due).days) for t in open_sorted if t.due and t.due < week_start]
    rolled = [row(t) for t in open_sorted
              if (t.due and week_start <= t.due <= friday + timedelta(days=2))
              or (t.status == "in_progress" and not (t.due and t.due < week_start))]
    next_start, next_end = friday + timedelta(days=3), friday + timedelta(days=9)
    ahead = [row(t) for t in open_sorted if t.due and next_start <= t.due <= next_end]

    def waiting_on(t: Task) -> list[str]:
        return [b for b in t.blocked_by if b in by_id and by_id[b].status not in CLEARED_STATUSES]

    stuck = [row(t, waiting_for=waiting_on(t)) for t in open_sorted if t.status == "waiting" or waiting_on(t)]

    cap = capacity["task_capacity_minutes"]
    return {
        "week_start": week_start.isoformat(),
        "week_end": friday.isoformat(),
        "capacity": capacity,
        "done": done_rows,
        "done_minutes": done_minutes,
        "done_without_completed_date": done_undated,
        "output_percent_of_task_capacity": round(100 * done_minutes / cap) if cap else None,
        "rolled_over": rolled,
        "overdue": overdue,
        "waiting_or_blocked": stuck,
        "due_next_week": ahead,
        "weekday_names": [weekday_name(d) for d in days],
    }
