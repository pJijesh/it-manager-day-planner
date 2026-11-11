"""The `init` command: write a starter profile, task list and a short note."""

from __future__ import annotations

from pathlib import Path

from .errors import InputError

STARTER_PROFILE = """{
  "_comment": "Edit this file. Times are 24-hour HH:MM. Fields starting with an underscore are ignored.",
  "name": "Your name",
  "organisation": "Your organisation",
  "working_hours": {
    "mon": ["08:30", "17:30"],
    "tue": ["08:30", "17:30"],
    "wed": ["08:30", "17:30"],
    "thu": ["08:30", "17:30"],
    "fri": ["08:30", "16:30"],
    "sat": null,
    "sun": null
  },
  "lunch": {"start": "12:30", "end": "13:15"},
  "buffer_percent": 30,
  "min_block_minutes": 30,
  "deep_work_window": {"start": "09:00", "end": "11:30"},
  "bank_holidays": [],
  "fixed_meetings": [
    {"title": "IT team stand-up", "weekdays": ["mon", "tue", "wed", "thu", "fri"], "start": "08:45", "end": "09:00"},
    {"title": "Weekly leadership meeting", "weekday": "mon", "start": "14:00", "end": "15:00"}
  ],
  "recurring_duties": [
    {"id": "alerts", "title": "Overnight alerts and backup check", "cadence": "daily", "minutes": 15, "preferred_start": "08:30"},
    {"id": "queue", "title": "Service desk queue and SLA check", "cadence": "daily", "minutes": 15, "preferred_start": "09:00"},
    {"id": "risks", "title": "Risk register review", "cadence": "weekly", "weekday": "thu", "minutes": 30},
    {"id": "kpi", "title": "Monthly KPI pack", "cadence": "monthly_last_working_day", "minutes": 60},
    {"id": "access", "title": "Access review sample", "cadence": "monthly_nth_weekday", "nth": 2, "weekday": "wed", "minutes": 45}
  ]
}
"""

STARTER_TASKS = """id,title,category,estimate_minutes,due,importance,status,blocked_by,earliest_start,created
T-001,Draft the infrastructure refresh proposal,deep,120,,4,todo,,,
T-002,Approve leaver requests,admin,20,,3,todo,,,
T-003,Review the supplier renewal terms,vendor,45,,3,todo,,,
T-004,Reply to the auditor's questions,compliance,60,,5,todo,T-003,,
"""

STARTER_README = """# Day planner workspace

Files in this folder:

- `profile.json`: your working hours, lunch, protected interruption buffer, deep-work window,
  fixed meetings and recurring duties. Edit it first.
- `tasks.csv`: your task list. Required columns: `id`, `title`, `estimate_minutes`. Optional:
  `category` (use `deep` for work that needs unbroken focus), `due` (YYYY-MM-DD), `importance`
  (1 to 5), `status` (todo, in_progress, waiting, done, cancelled), `blocked_by` (task ids
  separated by semicolons), `earliest_start`, `created`, `completed` and `actual_minutes`.

Try it:

```
python -m day_planner plan --profile profile.json --tasks tasks.csv --date 2026-10-26
python -m day_planner plan --profile profile.json --tasks tasks.csv --date 2026-10-26 --format html --out plan.html
python -m day_planner week --profile profile.json --tasks tasks.csv --start 2026-10-26
python -m day_planner review --profile profile.json --tasks tasks.csv --week-start 2026-10-26
```

Notes:

- `bank_holidays` is empty. Add the dates that apply to you as YYYY-MM-DD, taken from your official list.
- The starter duties and meetings are examples to replace, not recommendations.
- Everything stays on your machine. The tool reads these two files and writes only what you ask for.
"""

FILES = {"profile.json": STARTER_PROFILE, "tasks.csv": STARTER_TASKS, "README.md": STARTER_README}


def init_workspace(target: str | Path, force: bool = False) -> list[Path]:
    target = Path(target)
    if target.exists() and not target.is_dir():
        raise InputError(f"{target} exists and is not a folder")
    existing = [name for name in FILES if (target / name).exists()]
    if existing and not force:
        raise InputError(f"{target} already contains {', '.join(existing)}. Use --force to overwrite")
    target.mkdir(parents=True, exist_ok=True)
    written = []
    for name, text in FILES.items():
        path = target / name
        path.write_text(text, encoding="utf-8", newline="\n")
        written.append(path)
    return written
