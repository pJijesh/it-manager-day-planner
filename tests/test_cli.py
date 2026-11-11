"""Command line runs, including the worked example compared byte for byte with the committed outputs."""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from day_planner.cli import main

ROOT = Path(__file__).resolve().parent.parent
EX = ROOT / "examples"
OUT = EX / "output"
PROFILE, TASKS = str(EX / "profile.json"), str(EX / "tasks.csv")


def run_module(*args, cwd=ROOT):
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    return subprocess.run([sys.executable, "-m", "day_planner", *args], cwd=cwd, capture_output=True,
                          text=True, encoding="utf-8", env=env)


def load_regen():
    spec = importlib.util.spec_from_file_location("regenerate_examples", ROOT / "scripts" / "regenerate_examples.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_committed_example_output_matches_a_fresh_run(tmp_path):
    regen = load_regen()
    checked = []
    for args in regen.jobs():
        i = args.index("--out")
        committed = Path(args[i + 1])
        args = args[:i + 1] + [str(tmp_path / committed.name)] + args[i + 2:]
        assert main(args) == 0
        assert (tmp_path / committed.name).read_bytes() == committed.read_bytes(), committed.name
        checked.append(committed.name)
    assert len(checked) == 14
    for stem in ("plan-monday", "plan-incident-day", "plan-friday-month-end", "week-overview"):
        for ext in ("md", "html", "json"):
            assert f"{stem}.{ext}" in checked


def test_module_entry_point_end_to_end_plan():
    proc = run_module("plan", "--profile", PROFILE, "--tasks", TASKS, "--date", "2026-10-26", "--format", "json")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == (OUT / "plan-monday.json").read_text(encoding="utf-8")


def test_example_headline_values():
    monday = json.loads((OUT / "plan-monday.json").read_text(encoding="utf-8"))
    cap = monday["capacity"]
    assert (cap["working_minutes"], cap["meeting_minutes"], cap["duty_minutes"]) == (495, 75, 90)
    assert cap["buffer_target_minutes"] == 150 and cap["buffer_minutes"] == 150
    assert cap["task_minutes_planned"] == 180
    incident = json.loads((OUT / "plan-incident-day.json").read_text(encoding="utf-8"))
    assert incident["capacity"]["buffer_target_minutes"] == 250  # 50% of 495 is 247.5, rounded to 250
    assert incident["capacity"]["task_minutes_planned"] < monday["capacity"]["task_minutes_planned"]
    friday = json.loads((OUT / "plan-friday-month-end.json").read_text(encoding="utf-8"))
    assert "Month-end KPI pack" in [b["title"] for b in friday["blocks"]]
    assert "Month-end KPI pack" not in [b["title"] for b in monday["blocks"]]
    week = json.loads((OUT / "week-overview.json").read_text(encoding="utf-8"))
    assert [d["weekday"] for d in week["days"]] == ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    ids = {e["id"] for e in monday["excluded"]}
    assert ids == {"T-03", "T-12", "T-14", "T-17", "T-25"}  # blocked, waiting and not yet startable


def test_example_has_about_25_tasks_with_the_promised_mix():
    import csv
    rows = list(csv.DictReader((EX / "tasks.csv").open(encoding="utf-8")))
    assert 24 <= len(rows) <= 27
    assert any(r["blocked_by"] for r in rows)
    assert any(r["category"] == "deep" for r in rows)
    assert any(r["due"] and r["due"] < "2026-10-26" and r["status"] != "done" for r in rows)  # overdue on the Monday


def test_init_writes_a_working_starter_workspace(tmp_path):
    target = tmp_path / "ws"
    assert main(["init", str(target)]) == 0
    assert sorted(p.name for p in target.iterdir()) == ["README.md", "profile.json", "tasks.csv"]
    assert main(["plan", "--profile", str(target / "profile.json"), "--tasks", str(target / "tasks.csv"),
                 "--date", "2026-10-26", "--out", str(tmp_path / "plan.md")]) == 0
    assert "# Day plan: Monday 26 October 2026" in (tmp_path / "plan.md").read_text(encoding="utf-8")
    assert main(["week", "--profile", str(target / "profile.json"), "--tasks", str(target / "tasks.csv"),
                 "--start", "2026-10-26", "--format", "json", "--out", str(tmp_path / "w.json")]) == 0


def test_init_refuses_to_overwrite_without_force(tmp_path, capsys):
    main(["init", str(tmp_path)])
    capsys.readouterr()
    assert main(["init", str(tmp_path)]) == 2
    assert "--force" in capsys.readouterr().err
    assert main(["init", str(tmp_path), "--force"]) == 0


def test_out_option_writes_a_file_and_prints_a_summary(tmp_path, capsys):
    out = tmp_path / "sub" / "plan.html"
    assert main(["plan", "--profile", PROFILE, "--tasks", TASKS, "--date", "2026-10-26", "--format", "html", "--out", str(out)]) == 0
    assert out.read_text(encoding="utf-8").startswith("<!doctype html>")
    printed = capsys.readouterr().out
    assert "Monday 26 October 2026: 495 working min" in printed and "Wrote" in printed


def test_bad_input_exits_with_status_2_and_a_readable_message(tmp_path, capsys):
    bad = tmp_path / "t.csv"
    bad.write_text("id,title,estimate_minutes,blocked_by\nA,One,30,B\nB,Two,30,A\nC,Three,xx,\n", encoding="utf-8")
    assert main(["plan", "--profile", PROFILE, "--tasks", str(bad), "--date", "2026-10-26"]) == 2
    err = capsys.readouterr().err
    assert err.startswith("Error: 2 problems found:") and "circular blocking" in err and "line 4" in err


def test_missing_files_and_bad_dates(capsys):
    assert main(["plan", "--profile", "nope.json", "--tasks", TASKS, "--date", "2026-10-26"]) == 2
    assert "profile file not found" in capsys.readouterr().err
    with pytest.raises(SystemExit) as exc:
        main(["plan", "--profile", PROFILE, "--tasks", TASKS, "--date", "26/10/2026"])
    assert exc.value.code == 2
    assert "not a date, use YYYY-MM-DD" in capsys.readouterr().err


def test_week_start_must_be_monday(capsys):
    assert main(["week", "--profile", PROFILE, "--tasks", TASKS, "--start", "2026-10-28"]) == 2
    assert "is a Wednesday" in capsys.readouterr().err


def test_buffer_option_validation(capsys):
    with pytest.raises(SystemExit):
        main(["plan", "--profile", PROFILE, "--tasks", TASKS, "--date", "2026-10-26", "--buffer", "95"])
    assert "outside 0 to 90" in capsys.readouterr().err


def test_week_daily_option_adds_each_days_plan(capsys):
    assert main(["week", "--profile", PROFILE, "--tasks", TASKS, "--start", "2026-10-26", "--daily"]) == 0
    out = capsys.readouterr().out
    assert out.count("## Day plan: ") == 5


def test_rhythm_command(capsys):
    assert main(["rhythm", "--cadence", "monthly"]) == 0
    out = capsys.readouterr().out
    assert "## Monthly" in out and "## Daily" not in out and "suggestions to adapt" in out
    assert main(["rhythm", "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert [c["cadence"] for c in data["cadences"]] == ["daily", "weekly", "monthly", "quarterly", "annual"]


def test_review_command_prints_a_sheet(capsys):
    assert main(["review", "--profile", PROFILE, "--tasks", str(EX / "tasks-friday-snapshot.csv"), "--week-start", "2026-10-26"]) == 0
    out = capsys.readouterr().out
    assert "# Weekly review: 2026-10-26 to 2026-10-30" in out and "Reflection (fill in by hand)" in out


def test_console_script_is_declared_in_pyproject():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'day-planner = "day_planner.cli:main"' in text
    assert "dependencies = []" in text


def test_version_flag():
    proc = run_module("--version")
    assert proc.returncode == 0 and proc.stdout.startswith("day-planner ")
