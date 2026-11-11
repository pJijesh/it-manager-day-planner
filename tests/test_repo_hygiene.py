"""Checks on the written material: no long dashes, working links, diagrams, required files."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".venv", "venv", "build", "dist"}
TEXT_SUFFIXES = {".md", ".py", ".csv", ".json", ".yml", ".yaml", ".toml", ".mmd", ".txt", ".svg", ".html", ""}
LONG_DASHES = (chr(0x2014), chr(0x2013))


def text_files():
    for path in ROOT.rglob("*"):
        if not path.is_file() or SKIP_DIRS & set(path.relative_to(ROOT).parts):
            continue
        if path.suffix in TEXT_SUFFIXES and not any(part.endswith(".egg-info") for part in path.parts):
            yield path


def test_no_long_dashes_anywhere():
    bad = []
    for path in text_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if any(d in text for d in LONG_DASHES):
            bad.append(str(path.relative_to(ROOT)))
    assert not bad, f"long dashes found in: {bad}"


def test_markdown_relative_links_resolve():
    link = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
    problems = []
    for path in ROOT.rglob("*.md"):
        if SKIP_DIRS & set(path.relative_to(ROOT).parts):
            continue
        for target in link.findall(path.read_text(encoding="utf-8")):
            if re.match(r"^[a-z]+:", target) or target.startswith("#"):
                continue
            target = target.split("#")[0]
            if target and not (path.parent / target).exists():
                problems.append(f"{path.relative_to(ROOT)} -> {target}")
    assert not problems, problems


def test_markdown_images_exist_and_diagrams_have_sources():
    for name in ("day-flow", "placement"):
        assert (ROOT / "docs" / "images" / f"{name}.mmd").is_file()
        svg = (ROOT / "docs" / "images" / f"{name}.svg").read_text(encoding="utf-8")
        assert "<svg" in svg[:400]
    for png in ("day-plan-monday.png", "week-overview.png"):
        data = (ROOT / "docs" / "images" / png).read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n"


def test_required_files_exist():
    for name in ("README.md", "LICENSE", "CONTRIBUTING.md", ".gitignore", "pyproject.toml", ".github/workflows/test.yml",
                 "data/operating-rhythm.json", "docs/operating-rhythm.md", "docs/how-the-planner-works.md",
                 "docs/time-blocking-for-it-managers.md", "docs/getting-started.md"):
        assert (ROOT / name).is_file(), name
    templates = {p.name for p in (ROOT / "templates").glob("*.md")}
    assert templates == {"daily-plan.md", "end-of-day-shutdown.md", "weekly-review.md", "one-to-one-meeting-note.md",
                         "decision-log-entry.md", "incident-handover-note.md", "monthly-leadership-update.md"}


def test_licence_year_and_holder():
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "MIT License" in text and "Copyright (c) 2026 Puliyappottammal Jijesh" in text


def test_readme_follows_the_house_structure():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    lines = readme.splitlines()
    assert lines[0] == "# it-manager-day-planner"
    order = ["**Problem:**", "**For:**", "**Demonstrates:**", "## What it does", "## Quick start", "## How it is built",
             "## Design choices", "## Limitations", "## Verification status", "## Licence"]
    positions = [readme.index(marker) for marker in order]
    assert positions == sorted(positions)
    assert "fictional" in readme.lower()
    assert readme.index("## Verification status") < readme.index("## Roadmap") < readme.index("## Licence")


def test_no_python_cache_or_build_artifacts_are_tracked_by_gitignore_rules():
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for entry in ("__pycache__/", ".pytest_cache/", "*.egg-info/"):
        assert entry in ignore


def test_counts_quoted_in_the_readme_match_the_rhythm_data():
    import json
    data = json.loads((ROOT / "data" / "operating-rhythm.json").read_text(encoding="utf-8"))
    counts = {c["cadence"]: len(c["items"]) for c in data["cadences"]}
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert f"{sum(counts.values())} suggested items" in readme
    for cadence, n in counts.items():
        assert f"{n} {cadence}" in readme, cadence
