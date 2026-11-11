"""Regenerate the committed example outputs from the example inputs.

Run from the repository root:  python scripts/regenerate_examples.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from day_planner.cli import main  # noqa: E402

EX = ROOT / "examples"
OUT = EX / "output"
PROFILE = str(EX / "profile.json")
TASKS = str(EX / "tasks.csv")
SNAPSHOT = str(EX / "tasks-friday-snapshot.csv")

PLANS = [
    ("plan-monday", "2026-10-26", []),
    ("plan-incident-day", "2026-10-27", ["--buffer", "50"]),
    ("plan-friday-month-end", "2026-10-30", []),
]


def jobs():
    for name, day, extra in PLANS:
        for fmt in ("md", "html", "json"):
            yield ["plan", "--profile", PROFILE, "--tasks", TASKS, "--date", day, "--format", fmt,
                   "--out", str(OUT / f"{name}.{fmt}"), *extra]
    for fmt in ("md", "html", "json"):
        yield ["week", "--profile", PROFILE, "--tasks", TASKS, "--start", "2026-10-26", "--format", fmt,
               "--out", str(OUT / f"week-overview.{fmt}")]
    for fmt in ("md", "json"):
        yield ["review", "--profile", PROFILE, "--tasks", SNAPSHOT, "--week-start", "2026-10-26", "--format", fmt,
               "--out", str(OUT / f"weekly-review.{fmt}")]


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for args in jobs():
        code = main(args)
        if code:
            sys.exit(code)
