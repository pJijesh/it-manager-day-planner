"""Command line interface: init, plan, week, rhythm, review."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, render_html, render_json, render_md, rhythm
from .errors import InputError
from .profile import load_profile
from .review import build_review
from .scaffold import init_workspace
from .scheduler import plan_day
from .tasks import load_tasks
from .timeutil import long_date, parse_date
from .week import plan_week


def _date_arg(value: str):
    try:
        return parse_date(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None


def _percent_arg(value: str) -> float:
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not a number") from None
    if not 0 <= number <= 90:
        raise argparse.ArgumentTypeError(f"{value} is outside 0 to 90")
    return number


def _add_common(p: argparse.ArgumentParser, formats=("md", "html", "json")) -> None:
    p.add_argument("--profile", required=True, help="path to profile.json")
    p.add_argument("--tasks", required=True, help="path to tasks.csv")
    p.add_argument("--format", choices=formats, default="md", help="output format (default md)")
    p.add_argument("--out", help="write to this file instead of the terminal")
    p.add_argument("--buffer", type=_percent_arg, metavar="PERCENT",
                   help="override the profile's interruption buffer for this run, 0 to 90")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="day-planner",
        description="Build a realistic, time-blocked day or week plan for an IT manager from local files.",
    )
    parser.add_argument("--version", action="version", version=f"day-planner {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="write a starter profile.json, tasks.csv and README.md into a folder")
    p.add_argument("dir", help="folder to write into (created if needed)")
    p.add_argument("--force", action="store_true", help="overwrite existing files")

    p = sub.add_parser("plan", help="build the plan for one day")
    _add_common(p)
    p.add_argument("--date", required=True, type=_date_arg, help="the day to plan, YYYY-MM-DD")

    p = sub.add_parser("week", help="build a Monday to Friday overview")
    _add_common(p)
    p.add_argument("--start", required=True, type=_date_arg, help="the Monday the week starts, YYYY-MM-DD")
    p.add_argument("--daily", action="store_true", help="also include the full plan for each day")

    p = sub.add_parser("rhythm", help="print the operating-rhythm checklist")
    p.add_argument("--cadence", choices=rhythm.CADENCE_ORDER, help="show one cadence only")
    p.add_argument("--format", choices=("md", "json"), default="md")
    p.add_argument("--file", help="use this rhythm file instead of data/operating-rhythm.json")
    p.add_argument("--out", help="write to this file instead of the terminal")

    p = sub.add_parser("review", help="print a weekly review sheet")
    _add_common(p, formats=("md", "json"))
    p.add_argument("--week-start", required=True, type=_date_arg, help="the Monday of the week reviewed, YYYY-MM-DD")
    return parser


def _emit(text: str, out: str | None, summary: str) -> None:
    if out:
        path = Path(out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        print(f"{summary}\nWrote {path}")
    else:
        sys.stdout.write(text)


def _summary_day(plan) -> str:
    if not plan.working_day:
        return f"{long_date(plan.date)}: not a working day."
    c = plan.capacity
    text = (f"{long_date(plan.date)}: {c['working_minutes']} working min, {c['meeting_minutes']} meetings, "
            f"{c['duty_minutes']} duties, {c['buffer_minutes']} buffer, {c['task_minutes_planned']} tasks planned, "
            f"{len(plan.not_today)} not today.")
    alerts = [w for w in plan.warnings if w["level"] in ("alert", "warning")]
    return text + (f" {len(alerts)} warning(s)." if alerts else "")


def run(args: argparse.Namespace) -> int:
    if args.command == "init":
        for path in init_workspace(args.dir, args.force):
            print(f"Wrote {path}")
        return 0

    if args.command == "rhythm":
        data = rhythm.load_rhythm(args.file)
        if args.format == "json":
            blocks = rhythm.select(data, args.cadence)
            text = render_json.dumps({"note": data["note"], "cadences": blocks})
        else:
            text = rhythm.render_markdown(data, args.cadence)
        _emit(text, args.out, "Operating rhythm checklist.")
        return 0

    profile = load_profile(args.profile)
    tasks = load_tasks(args.tasks)

    if args.command == "plan":
        plan = plan_day(profile, tasks, args.date, args.buffer)
        if args.format == "html":
            text = render_html.render_day(plan)
        elif args.format == "json":
            text = render_json.dumps(render_json.day_to_dict(plan))
        else:
            text = render_md.render_day(plan)
        _emit(text, args.out, _summary_day(plan))
        return 0

    if args.command == "week":
        week = plan_week(profile, tasks, args.start, args.buffer)
        if args.format == "html":
            text = render_html.render_week(week, args.daily)
        elif args.format == "json":
            text = render_json.dumps(render_json.week_to_dict(week, args.daily))
        else:
            text = render_md.render_week(week, args.daily)
        s = week.summary
        summary = (f"Week from {long_date(week.start)}: {s['task_minutes_planned']} of {s['task_capacity_minutes']} task "
                   f"minutes planned, {s['tasks_not_scheduled']} task(s) not scheduled"
                   + (f", overloaded: {', '.join(s['overloaded_days'])}" if s["overloaded_days"] else "") + ".")
        _emit(text, args.out, summary)
        return 0

    if args.command == "review":
        review = build_review(profile, tasks, args.week_start, args.buffer)
        text = render_json.dumps(review) if args.format == "json" else render_md.render_review(review)
        summary = (f"Review for the week of {review['week_start']}: {len(review['done'])} done, "
                   f"{len(review['rolled_over'])} rolled over, {len(review['overdue'])} overdue.")
        _emit(text, args.out, summary)
        return 0
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        return run(args)
    except InputError as exc:
        print(exc.format(), file=sys.stderr)
        return 2
    except BrokenPipeError:  # for example piping into head
        return 0
