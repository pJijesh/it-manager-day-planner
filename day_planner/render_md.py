"""Markdown output for day plans, week overviews and weekly reviews."""

from __future__ import annotations

from .scheduler import DayPlan
from .timeutil import fmt_time, long_date, short_date
from .week import WeekPlan
from datetime import date

LEVEL_LABEL = {"alert": "ALERT", "warning": "Warning", "info": "Note"}
KIND_LABEL = {"meeting": "Meeting", "duty": "Duty", "lunch": "Lunch", "buffer": "Buffer", "task": "Task", "free": "Free"}

FOOTER = ("Plan built from local files by day-planner. Every placement has a reason, and the scoring and "
          "placement rules are in docs/how-the-planner-works.md.")


def cell(text: object) -> str:
    """Escape a value for a Markdown table cell."""
    return str(text).replace("\\", "\\\\").replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def _hm(minutes: int) -> str:
    """Minutes as '2 h 30 min' style text for summaries."""
    if minutes < 60:
        return f"{minutes} min"
    h, m = divmod(minutes, 60)
    return f"{h} h" if m == 0 else f"{h} h {m} min"


def render_day(plan: DayPlan, heading_level: int = 1) -> str:
    h1 = "#" * heading_level
    h2 = "#" * (heading_level + 1)
    lines = [f"{h1} Day plan: {long_date(plan.date)}", ""]
    who = ", ".join(x for x in (plan.name, plan.organisation) if x)
    if who:
        lines += [who, ""]
    for w in plan.warnings:
        lines.append(f"> **{LEVEL_LABEL[w['level']]}:** {w['message']}")
        lines.append("")
    if not plan.working_day:
        return "\n".join(lines).rstrip() + "\n"

    cap = plan.capacity
    start, end = plan.hours
    lines += [f"{h2} Capacity", "", "| Measure | Minutes |", "|---|---|"]
    lines.append(f"| Working time ({fmt_time(start)} to {fmt_time(end)}, lunch excluded) | {cap['working_minutes']} |")
    lines.append(f"| Fixed meetings | {cap['meeting_minutes']} |")
    lines.append(f"| Recurring duties | {cap['duty_minutes']} |")
    lines.append(f"| Interruptions and incidents (target {cap['buffer_target_minutes']}, from {_pct(plan.buffer_percent)}%) | {cap['buffer_minutes']} |")
    lines.append(f"| Planned task time | {cap['task_minutes_planned']} |")
    lines.append(f"| Free, unplanned | {cap['free_minutes']} |")
    lines.append("")
    lines += [f"{h2} Timeline", "", "| Time | Min | Block | Why |", "|---|---|---|---|"]
    for b in plan.blocks:
        box = "[ ] " if b.checkbox else ""
        part = f" ({b.part})" if b.part else ""
        label = f"{box}**{cell(b.title)}**{part}"
        extra = ""
        if b.kind == "task":
            extra = f", {cell(b.category)}"
        lines.append(f"| {fmt_time(b.start)} to {fmt_time(b.end)} | {b.minutes} | {label}{extra} | {cell(b.reason)} |")
    lines.append("")

    lines += [f"{h2} Not today", ""]
    if plan.not_today:
        lines += ["| Task | Needed | Placed | Why not | Suggested next |", "|---|---|---|---|---|"]
        for n in plan.not_today:
            suggested = _suggested(n)
            lines.append(f"| {cell(n['id'])} {cell(n['title'])} | {n['minutes_needed']} | {n['minutes_placed']} | "
                         f"{cell(n['reason'] + (' ' + n['note'] if n['note'] else ''))} | {suggested} |")
    else:
        lines.append("Every eligible task fits today.")
    lines.append("")

    lines += [f"{h2} Excluded from planning", ""]
    if plan.excluded:
        lines += ["| Task | Why excluded |", "|---|---|"]
        for e in plan.excluded:
            lines.append(f"| {cell(e['id'])} {cell(e['title'])} | {cell(e['reason'])} |")
    else:
        lines.append("Nothing is blocked, waiting or waiting for a start date.")
    lines += ["", FOOTER if heading_level == 1 else "", ]
    return "\n".join(lines).rstrip() + "\n"


def _suggested(n: dict) -> str:
    if not n.get("suggested_day"):
        return "No working day in the next three weeks"
    day = date.fromisoformat(n["suggested_day"])
    text = short_date(day)
    if n.get("planned_later"):
        text += " (planned in this week)"
    return text


def _pct(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


def render_week(week: WeekPlan, include_days: bool = False) -> str:
    lines = [f"# Week plan: {long_date(week.start)} to {long_date(week.end)}", ""]
    s = week.summary
    lines += [
        f"Working time {_hm(s['working_minutes'])}, of which meetings {_hm(s['meeting_minutes'])}, recurring duties "
        f"{_hm(s['duty_minutes'])} and protected buffer {_hm(s['buffer_minutes'])}. Task capacity "
        f"{_hm(s['task_capacity_minutes'])}, task time planned {_hm(s['task_minutes_planned'])}.",
        "",
    ]
    if s["overloaded_days"]:
        lines += [f"> **ALERT:** overloaded: {', '.join(s['overloaded_days'])}. Fixed commitments on those days exceed the working day.", ""]
    flagged = [d for d in s["flagged_days"] if d not in s["overloaded_days"]]
    if flagged:
        lines += [f"> **Warning:** check {', '.join(flagged)}. See the Flags column.", ""]
    lines += ["| Day | Working | Meetings | Duties | Buffer | Tasks | Free | Fixed % | Flags |", "|---|---|---|---|---|---|---|---|---|"]
    for r in week.rows:
        flags = "; ".join(r["flags"]) if r["flags"] else ""
        lines.append(f"| {r['weekday']} {r['date']} | {r['working_minutes']} | {r['meeting_minutes']} | {r['duty_minutes']} | "
                     f"{r['buffer_minutes']} | {r['task_minutes']} | {r['free_minutes']} | {r['fixed_percent']} | {cell(flags)} |")
    lines += ["", "All figures are minutes. Fixed % is meetings plus recurring duties as a share of working time.", ""]

    lines += ["## Tasks by day", ""]
    for r in week.rows:
        if not r["tasks"]:
            lines.append(f"- **{r['weekday']}:** none planned")
            continue
        items = "; ".join(f"{t['id']} {cell(t['title'])} ({t['minutes']} min)" for t in r["tasks"])
        lines.append(f"- **{r['weekday']}:** {items}")
    lines.append("")

    lines += ["## Not scheduled this week", ""]
    if week.not_scheduled:
        lines += ["| Task | Minutes left | Due | Why |", "|---|---|---|---|"]
        for n in week.not_scheduled:
            lines.append(f"| {cell(n['id'])} {cell(n['title'])} | {n['minutes_left']} | {n['due'] or 'none'} | {cell(n['reason'])} |")
    else:
        lines.append("Every eligible task is scheduled this week.")
    lines.append("")

    lines += ["## Excluded from planning", ""]
    if week.excluded:
        lines += ["| Task | Why excluded |", "|---|---|"]
        for e in week.excluded:
            lines.append(f"| {cell(e['id'])} {cell(e['title'])} | {cell(e['reason'])} |")
    else:
        lines.append("Nothing is blocked, waiting or waiting for a start date.")
    lines.append("")

    if include_days:
        for plan in week.days:
            lines += ["---", "", render_day(plan, heading_level=2).rstrip(), ""]
    lines.append(FOOTER)
    return "\n".join(lines).rstrip() + "\n"


def render_review(review: dict) -> str:
    cap = review["capacity"]
    lines = [f"# Weekly review: {review['week_start']} to {review['week_end']}", ""]
    lines += [
        "## Planned capacity against output", "",
        "| Measure | Minutes |", "|---|---|",
        f"| Working time (Monday to Friday, lunch excluded) | {cap['working_minutes']} |",
        f"| Fixed meetings | {cap['meeting_minutes']} |",
        f"| Recurring duties | {cap['duty_minutes']} |",
        f"| Interruptions and incidents (protected) | {cap['buffer_minutes']} |",
        f"| Task capacity (what was left for tasks) | {cap['task_capacity_minutes']} |",
        f"| Task output recorded as done | {review['done_minutes']} |",
    ]
    pct = review["output_percent_of_task_capacity"]
    lines += ["", ("Recorded output is " + f"{pct}% of task capacity. " if pct is not None else "") +
              "Output uses actual minutes where recorded and the estimate otherwise.", ""]
    if review["done_without_completed_date"]:
        lines += [f"Done without a completed date, so not counted: {', '.join(review['done_without_completed_date'])}.", ""]

    lines += ["## Done this week", ""]
    if review["done"]:
        lines += ["| Task | Completed | Minutes | Basis |", "|---|---|---|---|"]
        for r in review["done"]:
            lines.append(f"| {cell(r['id'])} {cell(r['title'])} | {r['completed']} | {r['minutes']} | {r['minutes_source']} |")
    else:
        lines.append("Nothing is recorded as done in this week.")
    lines.append("")

    def table(title: str, rows: list[dict], extra_head: str = "", extra=None, empty: str = "None.") -> None:
        lines.append(f"## {title}")
        lines.append("")
        if not rows:
            lines.extend([empty, ""])
            return
        head = "| Task | Importance | Due | Status |" + (f" {extra_head} |" if extra_head else "")
        lines.append(head)
        lines.append("|---|---|---|---|" + ("---|" if extra_head else ""))
        for r in rows:
            line = f"| {cell(r['id'])} {cell(r['title'])} | {r['importance']} | {r['due'] or 'none'} | {r['status']} |"
            if extra_head:
                line += f" {extra(r)} |"
            lines.append(line)
        lines.append("")

    table("Rolled over (due this week or in progress, not done)", review["rolled_over"],
          empty="Nothing rolled over.")
    table("Overdue (due before this week, still open)", review["overdue"], "Days late at week start",
          lambda r: str(r["days_late"]), empty="Nothing is overdue.")
    table("Waiting or blocked", review["waiting_or_blocked"], "Waiting for",
          lambda r: cell(", ".join(r["waiting_for"]) if r["waiting_for"] else "someone outside the team"),
          empty="Nothing is waiting or blocked.")
    table("Due next week", review["due_next_week"], empty="Nothing is due next week.")

    lines += [
        "## Reflection (fill in by hand)", "",
        "- Time lost to interruptions and incidents this week (minutes): ______",
        "- Was the protected buffer too big, too small or about right?",
        "- The biggest thing that was not planned:",
        "- One thing to say no to, delegate or renegotiate next week:",
        "- One change to the plan for next week:",
        "",
        FOOTER,
    ]
    return "\n".join(lines).rstrip() + "\n"
