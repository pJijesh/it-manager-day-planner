"""Load and validate tasks.csv."""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path

from .errors import InputError
from .model import Task
from .timeutil import parse_date

REQUIRED_COLUMNS = ("id", "title", "estimate_minutes")
OPTIONAL_COLUMNS = (
    "category", "due", "importance", "status", "blocked_by", "earliest_start", "created", "completed",
    "actual_minutes",
)
STATUSES = ("todo", "in_progress", "waiting", "done", "cancelled")
CLEARED_STATUSES = ("done", "cancelled")  # a blocker in one of these no longer blocks
DEFAULT_CATEGORY = "general"
DEFAULT_IMPORTANCE = 3


def load_tasks(path: str | Path) -> list[Task]:
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        raise InputError(f"tasks file not found: {path}") from None
    except OSError as exc:
        raise InputError(f"cannot read tasks file {path}: {exc.strerror or exc}") from None
    return parse_tasks(text, source=path.name)


def parse_tasks(text: str, source: str = "tasks.csv") -> list[Task]:
    reader = csv.DictReader(io.StringIO(text, newline=""))
    header = [h.strip() for h in (reader.fieldnames or [])]
    if not header:
        raise InputError(f"{source}: the file is empty. Expected a header row with at least: {', '.join(REQUIRED_COLUMNS)}")
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        raise InputError(f"{source}: missing required column(s): {', '.join(missing)}. Found: {', '.join(header)}")
    reader.fieldnames = header

    problems: list[str] = []
    tasks: list[Task] = []
    seen: dict[str, int] = {}
    for row in reader:
        line = reader.line_num
        if all((v or "").strip() == "" for v in row.values() if not isinstance(v, list)):
            continue

        def bad(column: str, message: str, line: int = line) -> None:
            problems.append(f"{source} line {line}, {column}: {message}")

        def cell(column: str) -> str:
            value = row.get(column)
            return value.strip() if isinstance(value, str) else ""

        ok = True
        task_id = cell("id")
        if not task_id:
            bad("id", "is empty")
            ok = False
        elif task_id in seen:
            bad("id", f"{task_id!r} is already used on line {seen[task_id]}")
            ok = False
        else:
            seen[task_id] = line
        title = cell("title")
        if not title:
            bad("title", "is empty")
            ok = False
        estimate = _int(cell("estimate_minutes"))
        if estimate is None or estimate < 1 or estimate > 2400:
            bad("estimate_minutes", f"{cell('estimate_minutes')!r} must be a whole number of minutes from 1 to 2400")
            ok = False
        importance_text = cell("importance")
        importance = DEFAULT_IMPORTANCE
        if importance_text:
            importance = _int(importance_text)
            if importance is None or not 1 <= importance <= 5:
                bad("importance", f"{importance_text!r} must be a whole number from 1 to 5")
                ok = False
        status = cell("status").lower() or "todo"
        if status not in STATUSES:
            bad("status", f"{cell('status')!r} is not one of: {', '.join(STATUSES)}")
            ok = False
        dates = {}
        for column in ("due", "earliest_start", "created", "completed"):
            value = cell(column)
            dates[column] = None
            if value:
                try:
                    dates[column] = parse_date(value)
                except ValueError as exc:
                    bad(column, str(exc))
                    ok = False
        actual = None
        if cell("actual_minutes"):
            actual = _int(cell("actual_minutes"))
            if actual is None or actual < 0:
                bad("actual_minutes", f"{cell('actual_minutes')!r} must be a whole number of minutes")
                ok = False
        blocked = tuple(b for b in re.split(r"[;,\s]+", cell("blocked_by")) if b)
        if ok:
            tasks.append(Task(
                id=task_id, title=title, category=cell("category") or DEFAULT_CATEGORY,
                estimate_minutes=estimate, due=dates["due"], importance=importance, status=status,
                blocked_by=blocked, earliest_start=dates["earliest_start"], created=dates["created"],
                completed=dates["completed"], actual_minutes=actual, line=line,
            ))

    problems.extend(_check_blocking(tasks, source))
    if not tasks and not problems:
        problems.append(f"{source}: no tasks found below the header row")
    if problems:
        raise InputError(problems)
    return tasks


def _int(text: str) -> int | None:
    if re.fullmatch(r"-?\d+", text or ""):
        return int(text)
    return None


def _check_blocking(tasks: list[Task], source: str) -> list[str]:
    problems = []
    by_id = {t.id: t for t in tasks}
    for task in tasks:
        for blocker in task.blocked_by:
            if blocker == task.id:
                problems.append(f"{source} line {task.line}, blocked_by: task {task.id} is blocked by itself")
            elif blocker not in by_id:
                problems.append(f"{source} line {task.line}, blocked_by: {blocker!r} is not a task id in this file")
    # Circular blocking: depth-first search over known ids, reporting each cycle once.
    state: dict[str, int] = {}
    reported: set[frozenset] = set()

    def visit(node: str, path: list[str]) -> None:
        state[node] = 1
        path.append(node)
        for nxt in by_id[node].blocked_by:
            if nxt not in by_id or nxt == node:
                continue
            if state.get(nxt) == 1:
                cycle = path[path.index(nxt):]
                key = frozenset(cycle)
                if key not in reported:
                    reported.add(key)
                    problems.append(
                        f"{source}: circular blocking: {' -> '.join(cycle + [nxt])}. "
                        "Each task waits for the next, so none can start. Remove one blocked_by link"
                    )
            elif state.get(nxt) is None:
                visit(nxt, path)
        path.pop()
        state[node] = 2

    for task in tasks:
        if state.get(task.id) is None:
            visit(task.id, [])
    return problems
