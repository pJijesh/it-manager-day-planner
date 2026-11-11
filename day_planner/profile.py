"""Load and validate profile.json."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from .errors import InputError
from .model import Duty, Meeting, Profile
from .timeutil import WEEKDAYS, WEEKDAY_NAMES, fmt_time, normalise_weekday, parse_date, parse_time, weekday_key

TOP_LEVEL_KEYS = {
    "name", "organisation", "working_hours", "lunch", "buffer_percent", "min_block_minutes",
    "buffer_block_minutes", "deep_work_window", "fixed_meetings", "recurring_duties", "bank_holidays",
}
CADENCES = (
    "daily", "weekdays", "weekly", "monthly_day", "monthly_last_working_day",
    "monthly_nth_weekday", "quarterly", "annual",
)
DUTY_KEYS = {
    "id", "title", "minutes", "cadence", "preferred_start", "weekdays", "weekday", "day",
    "last_working_day", "nth", "months", "month", "if_not_working", "notes",
}
MEETING_KEYS = {"title", "weekday", "weekdays", "date", "start", "end"}
DEFAULT_QUARTER_MONTHS = (1, 4, 7, 10)


def load_profile(path: str | Path) -> Profile:
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        raise InputError(f"profile file not found: {path}") from None
    except OSError as exc:
        raise InputError(f"cannot read profile file {path}: {exc.strerror or exc}") from None
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InputError(f"{path.name} is not valid JSON (line {exc.lineno}, column {exc.colno}): {exc.msg}") from None
    return parse_profile(raw, source=path.name)


def parse_profile(raw: object, source: str = "profile") -> Profile:
    problems: list[str] = []
    if not isinstance(raw, dict):
        raise InputError(f"{source}: the top level must be a JSON object")

    def bad(where: str, message: str) -> None:
        problems.append(f"{source}: {where}: {message}")

    for key in sorted(k for k in raw if k not in TOP_LEVEL_KEYS and not str(k).startswith("_")):
        bad(str(key), f"unknown field. Known fields: {', '.join(sorted(TOP_LEVEL_KEYS))}")

    name = raw.get("name", "")
    organisation = raw.get("organisation", "")
    for label, value in (("name", name), ("organisation", organisation)):
        if not isinstance(value, str):
            bad(label, "must be text")

    # Working hours
    hours: dict = {}
    wh = raw.get("working_hours")
    if not isinstance(wh, dict) or not wh:
        bad("working_hours", "required, for example {\"mon\": [\"09:00\", \"17:00\"]}")
    else:
        for key, value in wh.items():
            try:
                day = normalise_weekday(key)
            except ValueError as exc:
                bad(f"working_hours.{key}", str(exc))
                continue
            if value is None:
                continue
            if not (isinstance(value, (list, tuple)) and len(value) == 2):
                bad(f"working_hours.{key}", "must be [start, end] such as [\"09:00\", \"17:00\"], or null for a day off")
                continue
            try:
                start, end = parse_time(value[0]), parse_time(value[1])
            except ValueError as exc:
                bad(f"working_hours.{key}", str(exc))
                continue
            if end <= start:
                bad(f"working_hours.{key}", f"end {fmt_time(end)} must be after start {fmt_time(start)}")
                continue
            hours[day] = (start, end)
        if not hours and not any(p.startswith(f"{source}: working_hours") for p in problems):
            bad("working_hours", "at least one weekday needs working hours")

    # Lunch
    lunch = None
    if raw.get("lunch") is not None:
        lunch = _window(raw["lunch"], "lunch", bad)

    # Numbers
    buffer_percent = raw.get("buffer_percent", 30)
    if isinstance(buffer_percent, bool) or not isinstance(buffer_percent, (int, float)) or not (0 <= buffer_percent <= 90):
        bad("buffer_percent", f"{buffer_percent!r} must be a number from 0 to 90")
        buffer_percent = 30
    min_block = raw.get("min_block_minutes", 30)
    if isinstance(min_block, bool) or not isinstance(min_block, int) or not (5 <= min_block <= 240):
        bad("min_block_minutes", f"{min_block!r} must be a whole number of minutes from 5 to 240")
        min_block = 30
    buffer_block = raw.get("buffer_block_minutes", 60)
    if isinstance(buffer_block, bool) or not isinstance(buffer_block, int) or not (15 <= buffer_block <= 240):
        bad("buffer_block_minutes", f"{buffer_block!r} must be a whole number of minutes from 15 to 240")
        buffer_block = 60

    deep = None
    if raw.get("deep_work_window") is not None:
        deep = _window(raw["deep_work_window"], "deep_work_window", bad)

    # Bank holidays
    holidays: set[date] = set()
    bh = raw.get("bank_holidays", [])
    if not isinstance(bh, list):
        bad("bank_holidays", "must be a list of dates in YYYY-MM-DD form")
    else:
        for i, value in enumerate(bh):
            try:
                holidays.add(parse_date(value))
            except ValueError as exc:
                bad(f"bank_holidays[{i}]", str(exc))

    meetings = _meetings(raw.get("fixed_meetings", []), bad)
    duties = _duties(raw.get("recurring_duties", []), bad)

    if not problems:
        problems.extend(f"{source}: {p}" for p in _overlaps(meetings))

    if problems:
        raise InputError(problems)

    return Profile(
        name=name, organisation=organisation, hours=hours, lunch=lunch,
        buffer_percent=buffer_percent, min_block_minutes=min_block, buffer_block_minutes=buffer_block,
        deep_window=deep, meetings=tuple(meetings), duties=tuple(duties), bank_holidays=frozenset(holidays),
    )


def _window(value: object, where: str, bad) -> tuple[int, int] | None:
    if not isinstance(value, dict) or "start" not in value or "end" not in value:
        bad(where, "must be {\"start\": \"12:30\", \"end\": \"13:15\"} or null")
        return None
    try:
        start, end = parse_time(value["start"]), parse_time(value["end"])
    except ValueError as exc:
        bad(where, str(exc))
        return None
    if end <= start:
        bad(where, f"end {fmt_time(end)} must be after start {fmt_time(start)}")
        return None
    return (start, end)


def _meetings(raw: object, bad) -> list[Meeting]:
    out: list[Meeting] = []
    if not isinstance(raw, list):
        bad("fixed_meetings", "must be a list")
        return out
    for i, item in enumerate(raw):
        where = f"fixed_meetings[{i}]"
        if not isinstance(item, dict):
            bad(where, "must be an object with title, weekday or date, start and end")
            continue
        label = item.get("title") if isinstance(item.get("title"), str) and item.get("title").strip() else None
        where = f"fixed_meetings[{i}] ({label})" if label else where
        ok = True
        for key in sorted(k for k in item if k not in MEETING_KEYS and not str(k).startswith("_")):
            bad(where, f"unknown field {key!r}. Known fields: {', '.join(sorted(MEETING_KEYS))}")
            ok = False
        if label is None:
            bad(where, "title is required")
            ok = False
        given = [k for k in ("weekday", "weekdays", "date") if k in item]
        if len(given) != 1:
            bad(where, "give exactly one of weekday, weekdays or date")
            ok = False
        weekdays: tuple[str, ...] = ()
        on = None
        try:
            if "weekday" in item:
                weekdays = (normalise_weekday(item["weekday"]),)
            elif "weekdays" in item:
                if not isinstance(item["weekdays"], list) or not item["weekdays"]:
                    raise ValueError("weekdays must be a non-empty list such as [\"mon\", \"wed\"]")
                weekdays = tuple(sorted({normalise_weekday(w) for w in item["weekdays"]}, key=WEEKDAYS.index))
            elif "date" in item:
                on = parse_date(item["date"])
        except ValueError as exc:
            bad(where, str(exc))
            ok = False
        start = end = 0
        try:
            start, end = parse_time(item.get("start")), parse_time(item.get("end"))
            if end <= start:
                bad(where, f"end {fmt_time(end)} must be after start {fmt_time(start)}")
                ok = False
        except ValueError as exc:
            bad(where, str(exc))
            ok = False
        if ok:
            out.append(Meeting(title=label, start=start, end=end, weekdays=weekdays, on=on))
    return out


def meeting_applies(meeting: Meeting, day: date) -> bool:
    if meeting.on is not None:
        return meeting.on == day
    return weekday_key(day) in meeting.weekdays


def _overlaps(meetings: list[Meeting]) -> list[str]:
    """Two fixed meetings that could fall on the same day must not overlap."""
    problems = []
    for i, a in enumerate(meetings):
        for b in meetings[i + 1:]:
            if not (a.start < b.end and b.start < a.end):
                continue
            days_a = _day_set(a)
            days_b = _day_set(b)
            shared = _shared_day(a, b, days_a, days_b)
            if shared:
                problems.append(
                    f"fixed meetings overlap on {shared}: {a.title!r} ({fmt_time(a.start)} to {fmt_time(a.end)}) "
                    f"and {b.title!r} ({fmt_time(b.start)} to {fmt_time(b.end)}). Fixed meetings cannot share time, "
                    "so move one or drop one of them"
                )
    return problems


def _day_set(m: Meeting):
    return {weekday_key(m.on)} if m.on else set(m.weekdays)


def _shared_day(a: Meeting, b: Meeting, days_a, days_b) -> str:
    if a.on and b.on:
        return a.on.isoformat() if a.on == b.on else ""
    if a.on:
        return a.on.isoformat() if weekday_key(a.on) in days_b else ""
    if b.on:
        return b.on.isoformat() if weekday_key(b.on) in days_a else ""
    common = [d for d in WEEKDAYS if d in days_a and d in days_b]
    return WEEKDAY_NAMES[WEEKDAYS.index(common[0])] if common else ""


def _duties(raw: object, bad) -> list[Duty]:
    out: list[Duty] = []
    if not isinstance(raw, list):
        bad("recurring_duties", "must be a list")
        return out
    seen: set[str] = set()
    for i, item in enumerate(raw):
        where = f"recurring_duties[{i}]"
        if not isinstance(item, dict):
            bad(where, "must be an object")
            continue
        title = item.get("title")
        if isinstance(title, str) and title.strip():
            where = f"recurring_duties[{i}] ({title})"
        else:
            bad(where, "title is required")
            continue
        ok = True
        for key in sorted(k for k in item if k not in DUTY_KEYS and not str(k).startswith("_")):
            bad(where, f"unknown field {key!r}. Known fields: {', '.join(sorted(DUTY_KEYS))}")
            ok = False
        duty_id = item.get("id", f"duty-{i + 1}")
        if not isinstance(duty_id, str) or not duty_id.strip():
            bad(where, "id must be text")
            ok = False
        elif duty_id in seen:
            bad(where, f"id {duty_id!r} is used twice")
            ok = False
        else:
            seen.add(duty_id)
        minutes = item.get("minutes")
        if isinstance(minutes, bool) or not isinstance(minutes, int) or not (1 <= minutes <= 480):
            bad(where, f"minutes {minutes!r} must be a whole number from 1 to 480")
            ok = False
        cadence = item.get("cadence")
        if cadence not in CADENCES:
            bad(where, f"cadence {cadence!r} is not one of: {', '.join(CADENCES)}")
            continue
        preferred = None
        if item.get("preferred_start") is not None:
            try:
                preferred = parse_time(item["preferred_start"])
            except ValueError as exc:
                bad(where, f"preferred_start: {exc}")
                ok = False
        if_not = item.get("if_not_working", "next")
        if if_not not in ("next", "previous"):
            bad(where, f"if_not_working {if_not!r} must be \"next\" or \"previous\"")
            ok = False
        fields = _cadence_fields(cadence, item, where, bad)
        if fields is None or not ok:
            continue
        notes = item.get("notes", "")
        if not isinstance(notes, str):
            bad(where, "notes must be text")
            continue
        out.append(Duty(id=duty_id, title=title.strip(), minutes=minutes, cadence=cadence,
                        preferred_start=preferred, if_not_working=if_not, notes=notes, **fields))
    return out


def _day_rule(item: dict, where: str, bad) -> dict | None:
    """Exactly one of day, last_working_day, or nth plus weekday."""
    choices = []
    if "day" in item:
        choices.append("day")
    if item.get("last_working_day"):
        choices.append("last_working_day")
    if "nth" in item or ("weekday" in item and "nth" in item):
        choices.append("nth")
    if len(choices) != 1:
        bad(where, "give exactly one day rule: day, last_working_day, or nth with weekday")
        return None
    if choices[0] == "day":
        day = item["day"]
        if isinstance(day, bool) or not isinstance(day, int) or not (1 <= day <= 31):
            bad(where, f"day {day!r} must be a whole number from 1 to 31")
            return None
        return {"day": day}
    if choices[0] == "last_working_day":
        return {"last_working_day": True}
    nth = item["nth"]
    if isinstance(nth, bool) or not isinstance(nth, int) or nth not in (1, 2, 3, 4, 5, -1):
        bad(where, f"nth {nth!r} must be 1, 2, 3, 4, 5 or -1 (the last one in the month)")
        return None
    try:
        weekday = normalise_weekday(item.get("weekday"))
    except ValueError as exc:
        bad(where, f"weekday: {exc}")
        return None
    return {"nth": nth, "weekday": weekday}


def _cadence_fields(cadence: str, item: dict, where: str, bad) -> dict | None:
    if cadence == "daily":
        return {}
    if cadence == "weekdays":
        value = item.get("weekdays")
        if not isinstance(value, list) or not value:
            bad(where, "cadence weekdays needs weekdays, for example [\"mon\", \"thu\"]")
            return None
        try:
            days = tuple(sorted({normalise_weekday(v) for v in value}, key=WEEKDAYS.index))
        except ValueError as exc:
            bad(where, str(exc))
            return None
        return {"weekdays": days}
    if cadence == "weekly":
        try:
            return {"weekday": normalise_weekday(item.get("weekday"))}
        except ValueError as exc:
            bad(where, f"cadence weekly needs weekday: {exc}")
            return None
    if cadence == "monthly_day":
        if "day" not in item:
            bad(where, "cadence monthly_day needs day, a number from 1 to 31")
            return None
        return _day_rule({"day": item["day"]}, where, bad)
    if cadence == "monthly_last_working_day":
        return {"last_working_day": True}
    if cadence == "monthly_nth_weekday":
        if "nth" not in item:
            bad(where, "cadence monthly_nth_weekday needs nth and weekday")
            return None
        return _day_rule({"nth": item["nth"], "weekday": item.get("weekday")}, where, bad)
    # quarterly and annual share the day rules
    rule_source = {k: item[k] for k in ("day", "last_working_day", "nth", "weekday") if k in item}
    rule = _day_rule(rule_source, where, bad)
    if rule is None:
        return None
    if cadence == "quarterly":
        months = item.get("months", list(DEFAULT_QUARTER_MONTHS))
        if (not isinstance(months, list) or not months or len(set(months)) != len(months)
                or any(isinstance(m, bool) or not isinstance(m, int) or not 1 <= m <= 12 for m in months)):
            bad(where, "months must be a list of different month numbers from 1 to 12, for example [1, 4, 7, 10]")
            return None
        return {**rule, "months": tuple(sorted(months))}
    month = item.get("month")
    if isinstance(month, bool) or not isinstance(month, int) or not 1 <= month <= 12:
        bad(where, "cadence annual needs month, a number from 1 to 12")
        return None
    return {**rule, "month": month}
