"""JSON output. Key order is fixed and no timestamps are written, so output is byte-stable."""

from __future__ import annotations

import json

from .scheduler import DayPlan
from .timeutil import fmt_time, weekday_name
from .week import WeekPlan


def dumps(data: object) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def day_to_dict(plan: DayPlan) -> dict:
    hours = {"start": fmt_time(plan.hours[0]), "end": fmt_time(plan.hours[1])} if plan.hours else None
    deep = {"start": fmt_time(plan.deep_window[0]), "end": fmt_time(plan.deep_window[1])} if plan.deep_window else None
    return {
        "date": plan.date.isoformat(),
        "weekday": weekday_name(plan.date),
        "working_day": plan.working_day,
        "name": plan.name,
        "organisation": plan.organisation,
        "working_hours": hours,
        "deep_work_window": deep,
        "min_block_minutes": plan.min_block_minutes,
        "capacity": plan.capacity,
        "warnings": plan.warnings,
        "blocks": [
            {
                "start": fmt_time(b.start), "end": fmt_time(b.end), "minutes": b.minutes, "kind": b.kind,
                "title": b.title, "part": b.part, "task_id": b.task_id, "category": b.category,
                "deep": b.deep, "reason": b.reason,
            }
            for b in plan.blocks
        ],
        "not_today": plan.not_today,
        "excluded": plan.excluded,
        "ignored_done_or_cancelled_tasks": plan.ignored_done,
    }


def week_to_dict(week: WeekPlan, include_days: bool = False) -> dict:
    data = {
        "week_start": week.start.isoformat(),
        "week_end": week.end.isoformat(),
        "summary": week.summary,
        "days": week.rows,
        "not_scheduled_this_week": week.not_scheduled,
        "excluded": week.excluded,
    }
    if include_days:
        data["plans"] = [day_to_dict(p) for p in week.days]
    return data
