"""The operating-rhythm data and the document generated from it."""

import importlib.util
import json
from pathlib import Path

import pytest

from day_planner.errors import InputError
from day_planner.rhythm import CADENCE_ORDER, load_rhythm, validate_rhythm

ROOT = Path(__file__).resolve().parent.parent


def test_rhythm_file_is_valid_and_complete():
    data = load_rhythm(ROOT / "data" / "operating-rhythm.json")
    assert [c["cadence"] for c in data["cadences"]] == list(CADENCE_ORDER)
    assert all(len(c["items"]) >= 7 for c in data["cadences"])
    titles = " ".join(i["title"].lower() for c in data["cadences"] for i in c["items"])
    for needle in ("backup", "service desk", "security alerts", "change calendar", "certificates", "check-ins", "team meeting",
                   "one-to-ones", "vendor", "risk register", "budget", "patch", "kpi", "leadership report", "access review",
                   "licence", "restore", "supplier reviews", "policy review", "tabletop", "roadmap", "contract renewals",
                   "disaster recovery test", "certification"):
        assert needle in titles, needle


def test_note_says_these_are_suggestions_not_requirements():
    note = load_rhythm(ROOT / "data" / "operating-rhythm.json")["note"].lower()
    assert "suggestions" in note and "not standards" in note and "required by any law" in note


def test_no_item_claims_a_legal_or_standard_requirement():
    text = (ROOT / "data" / "operating-rhythm.json").read_text(encoding="utf-8").lower()
    body = text.split('"cadences"', 1)[1]
    for phrase in ("must be done", "is required by", "are required by", "mandatory", "legally", "regulation requires"):
        assert phrase not in body, phrase


def test_generated_document_is_up_to_date():
    spec = importlib.util.spec_from_file_location("build_rhythm_doc", ROOT / "scripts" / "build_rhythm_doc.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.build() == (ROOT / "docs" / "operating-rhythm.md").read_text(encoding="utf-8")


def test_stated_totals_in_intros_match_the_items():
    data = load_rhythm(ROOT / "data" / "operating-rhythm.json")
    daily = next(c for c in data["cadences"] if c["cadence"] == "daily")
    assert sum(i["typical_minutes"] for i in daily["items"]) == 80 and "80 minutes" in daily["intro"]


def test_validation_catches_problems(tmp_path):
    assert validate_rhythm({"cadences": []})[0].endswith("a 'note' saying these are suggestions is required")
    bad = {"note": "x", "cadences": [{"cadence": "daily", "items": [
        {"id": "D1", "title": "a", "why": "b", "typical_minutes": 5},
        {"id": "D1", "title": "a", "why": "", "typical_minutes": 0}]}]}
    text = "\n".join(validate_rhythm(bad))
    assert "used twice" in text and "missing why" in text and "typical_minutes" in text and "no items for cadence 'weekly'" in text
    path = tmp_path / "r.json"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(InputError):
        load_rhythm(path)
    with pytest.raises(InputError, match="not found"):
        load_rhythm(tmp_path / "none.json")


def test_every_rhythm_item_can_be_planned_as_a_duty():
    """The starter profile written by init uses rhythm ideas and must load."""
    from day_planner.profile import parse_profile
    from day_planner.scaffold import STARTER_PROFILE
    prof = parse_profile(json.loads(STARTER_PROFILE))
    assert {d.cadence for d in prof.duties} >= {"daily", "weekly", "monthly_last_working_day", "monthly_nth_weekday"}
