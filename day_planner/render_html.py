"""Single-file HTML output: A4, no JavaScript, checkboxes, light theme that prints well, dark mode on screen.

Every piece of user text goes through html.escape. There is no script element in the page.
"""

from __future__ import annotations

from datetime import date
from html import escape

from .scheduler import DayPlan
from .timeutil import fmt_time, long_date, short_date
from .week import WeekPlan

KIND_LABEL = {"meeting": "Meeting", "duty": "Duty", "lunch": "Lunch", "buffer": "Buffer", "task": "Task", "free": "Free"}
LEVEL_LABEL = {"alert": "Alert", "warning": "Warning", "info": "Note"}

CSS = """
:root {
  --bg: #ffffff; --fg: #1c2329; --muted: #55606a; --line: #cfd6dc; --soft: #f4f6f8;
  --meeting: #2b6cb0; --duty: #0f766e; --task: #2f855a; --deep: #6b46c1; --buffer: #b7791f;
  --lunch: #718096; --free: #a0aec0;
  --alert-bg: #fdecea; --alert-fg: #8a1f17; --warn-bg: #fff4d6; --warn-fg: #6b4300; --info-bg: #e8f1fb; --info-fg: #1e4a7a;
}
@media screen and (prefers-color-scheme: dark) {
  :root {
    --bg: #14181c; --fg: #e4e9ee; --muted: #9aa6b1; --line: #36404a; --soft: #1d2329;
    --meeting: #63a4e8; --duty: #4fd1c5; --task: #68d391; --deep: #b794f4; --buffer: #f6ad55;
    --lunch: #a0aec0; --free: #718096;
    --alert-bg: #3b1a17; --alert-fg: #ffb4aa; --warn-bg: #3a2c0e; --warn-fg: #f6d58e; --info-bg: #16283b; --info-fg: #a9cdf3;
  }
}
* { box-sizing: border-box; }
html { background: var(--bg); }
body {
  margin: 0 auto; padding: 14mm 12mm; max-width: 210mm; background: var(--bg); color: var(--fg);
  font: 10pt/1.35 system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  -webkit-print-color-adjust: exact; print-color-adjust: exact;
}
h1 { font-size: 17pt; margin: 0; letter-spacing: -0.01em; }
h2 { font-size: 10.5pt; margin: 9px 0 3px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); }
.sub { margin: 2px 0 8px; color: var(--muted); }
.stats { display: grid; grid-template-columns: repeat(6, 1fr); gap: 6px; margin: 6px 0; }
.stat { background: var(--soft); border: 1px solid var(--line); border-radius: 5px; padding: 4px 7px; }
.stat b { display: block; font-size: 13pt; line-height: 1.2; }
.stat span { font-size: 7.5pt; color: var(--muted); text-transform: uppercase; letter-spacing: 0.04em; }
.note { border-radius: 5px; padding: 5px 9px; margin: 5px 0; font-size: 9pt; border-left: 4px solid; }
.note.alert { background: var(--alert-bg); color: var(--alert-fg); border-color: var(--alert-fg); }
.note.warning { background: var(--warn-bg); color: var(--warn-fg); border-color: var(--warn-fg); }
.note.info { background: var(--info-bg); color: var(--info-fg); border-color: var(--info-fg); }
table { width: 100%; border-collapse: collapse; }
th { text-align: left; font-size: 7.5pt; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); border-bottom: 1px solid var(--line); padding: 3px 5px; }
td { padding: 2px 5px; border-bottom: 1px solid var(--line); vertical-align: top; }
td.time { white-space: nowrap; font-variant-numeric: tabular-nums; width: 24mm; }
td.min { white-space: nowrap; text-align: right; width: 10mm; color: var(--muted); font-variant-numeric: tabular-nums; }
td.box { width: 6mm; }
td.num { text-align: right; font-variant-numeric: tabular-nums; }
.timeline td:first-child { border-left: 4px solid var(--free); }
.timeline tr.meeting td:first-child { border-left-color: var(--meeting); }
.timeline tr.duty td:first-child { border-left-color: var(--duty); }
.timeline tr.task td:first-child { border-left-color: var(--task); }
.timeline tr.deep td:first-child { border-left-color: var(--deep); }
.timeline tr.buffer td:first-child { border-left-color: var(--buffer); }
.timeline tr.lunch td:first-child { border-left-color: var(--lunch); }
.timeline tr.buffer td, .timeline tr.lunch td { background: var(--soft); }
.timeline tr.free td { color: var(--muted); }
.tag { display: inline-block; font-size: 7pt; text-transform: uppercase; letter-spacing: 0.05em; border: 1px solid var(--line); border-radius: 3px; padding: 0 4px; margin-left: 5px; color: var(--muted); vertical-align: 1px; }
.title { font-weight: 600; }
.why { font-size: 7.5pt; color: var(--muted); margin-top: 1px; }
input[type=checkbox] { width: 11px; height: 11px; margin: 2px 0 0; }
.lines { margin-top: 4px; }
.lines div { border-bottom: 1px solid var(--line); height: 6mm; }
ul.excluded { list-style: none; margin: 0; padding: 0; columns: 2; column-gap: 12px; }
ul.excluded li { break-inside: avoid; padding: 2px 0; border-bottom: 1px solid var(--line); }
.small { font-size: 8pt; color: var(--muted); }
footer { margin-top: 10px; font-size: 7.5pt; color: var(--muted); }
.flag { font-weight: 700; color: var(--alert-fg); }
tr, .note, .stat { break-inside: avoid; }
.page + .page { break-before: page; margin-top: 18px; }
@page { size: A4; margin: 7mm 8mm; }
@media print {
  html, body { background: #fff; }
  body { max-width: none; padding: 0; font-size: 8.5pt; }
  h1 { font-size: 15pt; }
  .stat b { font-size: 11pt; }
  .why { font-size: 7pt; }
  td { padding: 1.5px 5px; }
  .lines div { height: 5mm; }
  footer { margin-top: 4px; }
}
"""

NOT_TODAY_ROWS = 3  # the printable page shows the highest-scoring tasks that did not fit; Markdown and JSON list all

GENERIC_REASON = "No time left after meetings, duties, the buffer and higher-scoring tasks."

FOOTER = ("Plan built from local files by day-planner. Every placement has a reason; the rules are in "
          "docs/how-the-planner-works.md.")


def _page(title: str, body: str, lang_title: str = "") -> str:
    return (
        "<!doctype html>\n<html lang=\"en-GB\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        "<meta name=\"color-scheme\" content=\"light dark\">\n"
        f"<title>{escape(title)}</title>\n<style>{CSS}</style>\n</head>\n<body>\n{body}</body>\n</html>\n"
    )


def _notes(warnings: list[dict]) -> str:
    return "".join(
        f'<div class="note {escape(w["level"])}"><strong>{LEVEL_LABEL[w["level"]]}:</strong> {escape(w["message"])}</div>\n'
        for w in warnings
    )


def _day_section(plan: DayPlan, first: bool = True) -> str:
    out = ['<section class="page">\n']
    who = ", ".join(x for x in (plan.name, plan.organisation) if x)
    out.append(f"<h1>Day plan: {escape(long_date(plan.date))}</h1>\n")
    if who:
        out.append(f'<p class="sub">{escape(who)}</p>\n')
    out.append(_notes(plan.warnings))
    if not plan.working_day:
        out.append("</section>\n")
        return "".join(out)

    cap = plan.capacity
    start, end = plan.hours
    stats = [
        (cap["working_minutes"], f"Working min ({fmt_time(start)} to {fmt_time(end)})"),
        (cap["meeting_minutes"], "Meetings min"),
        (cap["duty_minutes"], "Duties min"),
        (cap["buffer_minutes"], f"Buffer min (target {cap['buffer_target_minutes']})"),
        (cap["task_minutes_planned"], "Tasks planned min"),
        (cap["free_minutes"], "Free min"),
    ]
    out.append('<div class="stats">' + "".join(f"<div class=\"stat\"><b>{v}</b><span>{escape(label)}</span></div>" for v, label in stats) + "</div>\n")

    out.append('<table class="timeline">\n<thead><tr><th>Time</th><th>Min</th><th></th><th>Block and reason</th></tr></thead>\n<tbody>\n')
    for b in plan.blocks:
        css = "deep" if (b.kind == "task" and b.deep) else b.kind
        tag = KIND_LABEL[b.kind] + (" (deep)" if b.deep else "")
        box = '<input type="checkbox" aria-label="Done">' if b.checkbox else ""
        part = f" <span class=\"small\">({escape(b.part)})</span>" if b.part else ""
        cat = f' <span class="small">{escape(b.category)}</span>' if b.kind == "task" and b.category else ""
        inline, why = _split_reason(b)
        inline_html = f' <span class="small">{escape(inline)}</span>' if inline else ""
        why_html = f'<div class="why">{escape(why)}</div>' if why else ""
        out.append(
            f'<tr class="{css}"><td class="time">{fmt_time(b.start)} to {fmt_time(b.end)}</td>'
            f'<td class="min">{b.minutes}</td><td class="box">{box}</td>'
            f'<td><span class="title">{escape(b.title)}</span>{part}{cat}<span class="tag">{escape(tag)}</span>'
            f'{inline_html}{why_html}</td></tr>\n'
        )
    out.append("</tbody></table>\n")

    out.append("<h2>Not today</h2>\n")
    if plan.not_today:
        out.append('<table><thead><tr><th>Task</th><th>Need</th><th>Placed</th><th>Next</th><th>Note</th></tr></thead><tbody>\n')
        for n in plan.not_today[:NOT_TODAY_ROWS]:
            note = "" if n["reason"] == GENERIC_REASON else n["reason"]
            if n["note"]:
                note = (note + " " + n["note"]).strip()
            out.append(
                f"<tr><td><span class=\"title\">{escape(n['title'])}</span> <span class=\"small\">{escape(n['id'])}</span></td>"
                f"<td class=\"num\">{n['minutes_needed']}</td><td class=\"num\">{n['minutes_placed']}</td>"
                f"<td class=\"time\">{escape(_suggested(n))}</td><td><div class=\"why\">{escape(note)}</div></td></tr>\n"
            )
        out.append("</tbody></table>\n")
        out.append(f'<p class="small">Unless a note says otherwise: {escape(GENERIC_REASON[0].lower() + GENERIC_REASON[1:])}</p>\n')
        rest = plan.not_today[NOT_TODAY_ROWS:]
        if rest:
            names = ", ".join(f"{n['id']} ({n['minutes_needed']} min)" for n in rest)
            out.append(f'<p class="small">{len(rest)} more with lower scores (titles are in the Markdown and JSON output): {escape(names)}.</p>\n')
    else:
        out.append('<p class="small">Every eligible task fits today.</p>\n')

    out.append("<h2>Excluded from planning</h2>\n")
    if plan.excluded:
        out.append('<ul class="excluded">\n')
        for e in plan.excluded:
            out.append(f"<li><span class=\"title\">{escape(e['title'])}</span> <span class=\"small\">{escape(e['id'])}</span>"
                       f"<div class=\"why\">{escape(e['reason'])}</div></li>\n")
        out.append("</ul>\n")
    else:
        out.append('<p class="small">Nothing is blocked, waiting or waiting for a start date.</p>\n')

    out.append("<h2>Notes</h2>\n<div class=\"lines\"><div></div></div>\n")
    if first:
        out.append(f"<footer>{escape(FOOTER)}</footer>\n")
    out.append("</section>\n")
    return "".join(out)


def _split_reason(b) -> tuple[str, str]:
    """Return (short text shown on the title line, longer text shown beneath). Tasks keep the full reason."""
    r = b.reason
    if b.kind == "task":
        return "", r
    if b.kind == "duty":
        head, _, rest = r.partition(". ")
        inline = head.replace("Recurring duty, ", "")
        return inline, ("" if "preferred start, " in rest and "not free" not in rest else rest)
    if b.kind == "buffer":
        if r.startswith("Protected buffer: "):
            return r[len("Protected buffer: "):].split(";")[0], ""
        return r.replace(" is shorter than the", ", shorter than the").replace(", so it is counted as buffer.", ", counted as buffer."), ""
    if b.kind == "meeting":
        return "", ("" if r == "Fixed meeting from the profile." else r)
    if b.kind == "lunch":
        return "", ""
    return r, ""


def _suggested(n: dict) -> str:
    if not n.get("suggested_day"):
        return "no working day in the next three weeks"
    text = short_date(date.fromisoformat(n["suggested_day"]))
    return text + (" (planned in this week)" if n.get("planned_later") else "")


def render_day(plan: DayPlan) -> str:
    return _page(f"Day plan {plan.date.isoformat()}", _day_section(plan))


def render_week(week: WeekPlan, include_days: bool = False) -> str:
    s = week.summary
    out = ['<section class="page">\n']
    out.append(f"<h1>Week plan: {escape(long_date(week.start))} to {escape(long_date(week.end))}</h1>\n")
    stats = [
        (s["working_minutes"], "Working min"), (s["meeting_minutes"], "Meetings min"), (s["duty_minutes"], "Duties min"),
        (s["buffer_minutes"], "Buffer min"), (s["task_capacity_minutes"], "Task capacity min"),
        (s["task_minutes_planned"], "Tasks planned min"),
    ]
    out.append('<div class="stats">' + "".join(f"<div class=\"stat\"><b>{v}</b><span>{escape(label)}</span></div>" for v, label in stats) + "</div>\n")
    if s["overloaded_days"]:
        out.append(f'<div class="note alert"><strong>Alert:</strong> overloaded: {escape(", ".join(s["overloaded_days"]))}. '
                   "Fixed commitments on those days exceed the working day.</div>\n")
    flagged = [d for d in s["flagged_days"] if d not in s["overloaded_days"]]
    if flagged:
        out.append(f'<div class="note warning"><strong>Warning:</strong> check {escape(", ".join(flagged))}. See the Flags column.</div>\n')
    out.append('<table><thead><tr><th>Day</th><th>Work</th><th>Meet</th><th>Duty</th><th>Buffer</th><th>Tasks</th><th>Free</th><th>Fixed %</th><th>Flags</th></tr></thead><tbody>\n')
    for r in week.rows:
        flags = "; ".join(r["flags"])
        out.append(
            f"<tr><td style=\"width:42mm\"><span class=\"title\">{escape(r['weekday'])}</span> <span class=\"small\" style=\"white-space:nowrap\">{escape(r['date'])}</span></td>"
            + "".join(f"<td class=\"num\">{r[k]}</td>" for k in ("working_minutes", "meeting_minutes", "duty_minutes", "buffer_minutes", "task_minutes", "free_minutes", "fixed_percent"))
            + f"<td class=\"flag\">{escape(flags)}</td></tr>\n"
        )
    out.append('</tbody></table>\n<p class="small">Minutes, except Fixed %, which is meetings plus recurring duties as a share of working time.</p>\n')

    out.append("<h2>Tasks by day</h2>\n<table><tbody>\n")
    for r in week.rows:
        if r["tasks"]:
            items = "; ".join(f"{t['title']} ({t['minutes']} min)" for t in r["tasks"])
        else:
            items = "none planned"
        out.append(f"<tr><td style=\"width:22mm\"><span class=\"title\">{escape(r['weekday'])}</span></td><td>{escape(items)}</td></tr>\n")
    out.append("</tbody></table>\n")

    out.append("<h2>Not scheduled this week</h2>\n")
    if week.not_scheduled:
        out.append('<ul class="excluded">\n')
        for n in week.not_scheduled:
            due = f", due {escape(n['due'])}" if n["due"] else ""
            out.append(f"<li><span class=\"title\">{escape(n['title'])}</span> <span class=\"small\">{escape(n['id'])}</span>"
                       f"<div class=\"why\">{n['minutes_left']} of {n['minutes_needed']} min left{due}</div></li>\n")
        out.append("</ul>\n")
        out.append('<p class="small">These found no time after meetings, duties, the buffer and higher-scoring tasks.</p>\n')
    else:
        out.append('<p class="small">Every eligible task is scheduled this week.</p>\n')

    out.append("<h2>Excluded from planning</h2>\n")
    if week.excluded:
        out.append('<ul class="excluded">\n')
        for e in week.excluded:
            out.append(f"<li><span class=\"title\">{escape(e['title'])}</span> <span class=\"small\">{escape(e['id'])}</span>"
                       f"<div class=\"why\">{escape(e['reason'])}</div></li>\n")
        out.append("</ul>\n")
    else:
        out.append('<p class="small">Nothing is blocked, waiting or waiting for a start date.</p>\n')
    out.append(f"<footer>{escape(FOOTER)}</footer>\n</section>\n")
    if include_days:
        for plan in week.days:
            out.append(_day_section(plan, first=False))
    return _page(f"Week plan {week.start.isoformat()}", "".join(out))
