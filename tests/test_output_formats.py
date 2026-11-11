"""Markdown, JSON and HTML output, including escaping of untrusted text."""

import json
import re
from datetime import date

from day_planner import render_html, render_json, render_md
from day_planner.scheduler import plan_day
from day_planner.week import plan_week
from helpers import profile, tasks

MON = date(2026, 10, 26)
SCRIPT = "<script>alert('x')</script>"


def nasty_plan():
    p = profile(
        name=f"{SCRIPT} Manager",
        organisation="A & B <Ltd>",
        fixed_meetings=[{"title": "<img src=x onerror=alert(1)>", "weekday": "mon", "start": "10:00", "end": "11:00"}],
        recurring_duties=[{"title": "Check <b>bold</b>", "cadence": "daily", "minutes": 15, "preferred_start": "09:00"}],
    )
    t = tasks(
        f'A,"{SCRIPT}",60,"cat<script>",2026-10-26,5,todo,,,\n'
        f'B,"Pipe | in title",30,admin,,3,todo,,,\n'
        f'C,"Overflow {SCRIPT}",2000,admin,,1,todo,,,\n'
        f'D,"Blocked {SCRIPT}",30,admin,,3,todo,A,,'
    )
    return plan_day(p, t, MON)


def test_html_escapes_every_piece_of_text():
    html = render_html.render_day(nasty_plan())
    assert "<script" not in html.lower()
    assert "&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt;" in html
    assert "&lt;img src=x onerror=alert(1)&gt;" in html
    assert "Check &lt;b&gt;bold&lt;/b&gt;" in html
    assert "A &amp; B &lt;Ltd&gt;" in html
    assert "<img" not in html and "<b>bold" not in html


def test_html_escapes_in_week_view_too():
    t = tasks(f'A,"{SCRIPT}",60,admin,,5,todo,,,')
    week = plan_week(profile(name=SCRIPT), t, MON)
    html = render_html.render_week(week, include_days=True)
    assert "<script" not in html.lower() and "&lt;script&gt;" in html


def test_html_is_a_printable_single_file():
    html = render_html.render_day(plan_day(profile(), tasks("A,Task,60,admin,,3,todo,,,"), MON))
    assert html.startswith("<!doctype html>")
    assert "size: A4" in html and "@page" in html
    assert 'type="checkbox"' in html
    assert "prefers-color-scheme: dark" in html
    assert "<script" not in html and "javascript" not in html.lower()
    assert "<link" not in html and "http://" not in html and "https://" not in html  # no external resources
    assert re.search(r"<title>Day plan 2026-10-26</title>", html)


def test_markdown_escapes_table_pipes():
    md = render_md.render_day(nasty_plan())
    assert "Pipe \\| in title" in md
    assert "| Pipe | in title" not in md


def test_markdown_shows_checkboxes_reasons_and_sections():
    md = render_md.render_day(plan_day(profile(), tasks("A,Task,60,admin,,3,todo,,,"), MON))
    assert md.startswith("# Day plan: Monday 26 October 2026")
    for heading in ("## Capacity", "## Timeline", "## Not today", "## Excluded from planning"):
        assert heading in md
    assert "[ ] **Task**" in md
    assert "Score 30: importance 3 gives 30" in md


def test_json_structure_and_reasons():
    data = json.loads(render_json.dumps(render_json.day_to_dict(nasty_plan())))
    assert data["date"] == "2026-10-26" and data["weekday"] == "Monday"
    assert set(data) >= {"capacity", "warnings", "blocks", "not_today", "excluded", "working_hours", "deep_work_window"}
    assert all(b["reason"] for b in data["blocks"])
    assert {b["kind"] for b in data["blocks"]} >= {"meeting", "duty", "lunch", "buffer", "task"}
    assert data["not_today"][0]["suggested_day"] == "2026-10-27"
    assert render_json.dumps(data).endswith("}\n")


def test_buffer_blocks_are_named_interruptions_and_incidents():
    plan = plan_day(profile(), [], MON)
    titles = {b.title for b in plan.blocks if b.kind == "buffer"}
    assert titles == {"Interruptions and incidents"}


def test_non_working_day_renders_in_all_formats():
    plan = plan_day(profile(), [], date(2026, 10, 24))
    assert "not a working day" in render_md.render_day(plan)
    assert "not a working day" in render_html.render_day(plan)
    assert json.loads(render_json.dumps(render_json.day_to_dict(plan)))["working_day"] is False
