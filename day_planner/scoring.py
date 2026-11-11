"""The task score. Whole numbers only, so every score can be checked by hand.

    score = importance points + urgency points + age points

Importance points: 10 x importance (1 to 5), so 10 to 50.

Urgency points, from the number of calendar days between the plan date and the due date:
    overdue by n days  : 40 + min(20, 2 x n)       (41 to 60)
    due today          : 40
    due in n days      : max(0, 40 - 5 x n)        (35 for tomorrow, 0 from 8 days away)
    no due date        : 0

Age points: one point for each full 7 days since the task was created, capped at 10.
No created date means 0 age points.

Tie-break, in order: earlier due date (no due date last), higher importance,
shorter estimate, then the task id in natural order (T-2 before T-10).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from .model import Task

IMPORTANCE_WEIGHT = 10
DUE_TODAY_POINTS = 40
OVERDUE_POINTS_PER_DAY = 2
OVERDUE_BONUS_CAP = 20
URGENCY_DROP_PER_DAY = 5
AGE_POINTS_CAP = 10
AGE_DAYS_PER_POINT = 7


@dataclass(frozen=True)
class Score:
    total: int
    importance_points: int
    urgency_points: int
    age_points: int
    urgency_note: str

    def explain(self) -> str:
        parts = [f"importance {self.importance_points // IMPORTANCE_WEIGHT} gives {self.importance_points}",
                 f"{self.urgency_note} gives {self.urgency_points}"]
        if self.age_points:
            parts.append(f"age gives {self.age_points}")
        return f"Score {self.total}: " + ", ".join(parts)


def score_task(task: Task, on: date) -> Score:
    importance_points = IMPORTANCE_WEIGHT * task.importance
    if task.due is None:
        urgency, note = 0, "no due date"
    else:
        days = (task.due - on).days
        if days < 0:
            late = -days
            urgency = DUE_TODAY_POINTS + min(OVERDUE_BONUS_CAP, OVERDUE_POINTS_PER_DAY * late)
            note = f"overdue by {late} day{'s' if late != 1 else ''}"
        elif days == 0:
            urgency, note = DUE_TODAY_POINTS, "due today"
        else:
            urgency = max(0, DUE_TODAY_POINTS - URGENCY_DROP_PER_DAY * days)
            note = f"due in {days} day{'s' if days != 1 else ''}"
    age = 0
    if task.created is not None:
        age = min(AGE_POINTS_CAP, max(0, (on - task.created).days) // AGE_DAYS_PER_POINT)
    return Score(importance_points + urgency + age, importance_points, urgency, age, note)


def natural_key(text: str) -> tuple:
    """Sort key that orders T-2 before T-10. The parts alternate text, number, text, so types line up."""
    return tuple(int(p) if i % 2 else p.lower() for i, p in enumerate(re.split(r"(\d+)", text)))


def sort_key(task: Task, score: Score) -> tuple:
    return (
        -score.total,
        task.due or date.max,
        -task.importance,
        task.estimate_minutes,
        natural_key(task.id),
    )
