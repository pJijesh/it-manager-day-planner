"""Load and print the operating-rhythm checklist from data/operating-rhythm.json."""

from __future__ import annotations

import json
from pathlib import Path

from .errors import InputError

CADENCE_ORDER = ("daily", "weekly", "monthly", "quarterly", "annual")


def default_rhythm_path() -> Path:
    """data/operating-rhythm.json beside the package (a checkout or editable install), else in the working folder."""
    beside_package = Path(__file__).resolve().parent.parent / "data" / "operating-rhythm.json"
    if beside_package.is_file():
        return beside_package
    return Path.cwd() / "data" / "operating-rhythm.json"


def load_rhythm(path: str | Path | None = None) -> dict:
    path = Path(path) if path else default_rhythm_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise InputError(f"operating rhythm file not found: {path}. Run from the repository folder or pass --file") from None
    except json.JSONDecodeError as exc:
        raise InputError(f"{path.name} is not valid JSON (line {exc.lineno}, column {exc.colno}): {exc.msg}") from None
    problems = validate_rhythm(data, path.name)
    if problems:
        raise InputError(problems)
    return data


def validate_rhythm(data: object, source: str = "operating-rhythm.json") -> list[str]:
    problems: list[str] = []
    if not isinstance(data, dict) or not isinstance(data.get("cadences"), list):
        return [f"{source}: expected an object with a 'cadences' list"]
    if not isinstance(data.get("note"), str) or not data["note"].strip():
        problems.append(f"{source}: a 'note' saying these are suggestions is required")
    seen_ids: set[str] = set()
    seen_cadences: set[str] = set()
    for block in data["cadences"]:
        cadence = block.get("cadence") if isinstance(block, dict) else None
        if cadence not in CADENCE_ORDER:
            problems.append(f"{source}: unknown cadence {cadence!r}")
            continue
        seen_cadences.add(cadence)
        for item in block.get("items", []):
            for key in ("id", "title", "why"):
                if not isinstance(item.get(key), str) or not item[key].strip():
                    problems.append(f"{source}: {cadence} item {item.get('id', '?')} is missing {key}")
            item_id = item.get("id")
            if item_id in seen_ids:
                problems.append(f"{source}: id {item_id!r} is used twice")
            seen_ids.add(item_id)
            minutes = item.get("typical_minutes")
            if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes < 1:
                problems.append(f"{source}: {item_id} typical_minutes must be a positive whole number")
    for cadence in CADENCE_ORDER:
        if cadence not in seen_cadences:
            problems.append(f"{source}: no items for cadence {cadence!r}")
    return problems


def select(data: dict, cadence: str | None) -> list[dict]:
    blocks = {b["cadence"]: b for b in data["cadences"]}
    names = [cadence] if cadence else [c for c in CADENCE_ORDER if c in blocks]
    return [blocks[c] for c in names if c in blocks]


def render_markdown(data: dict, cadence: str | None = None) -> str:
    lines = ["# Operating rhythm checklist", "", f"> {data['note']}", ""]
    for block in select(data, cadence):
        items = block["items"]
        total = sum(i["typical_minutes"] for i in items)
        lines += [f"## {block['label']}", "", block.get("intro", ""), ""] if block.get("intro") else [f"## {block['label']}", ""]
        for item in items:
            when = f" ({item['suggested_when']})" if item.get("suggested_when") else ""
            lines.append(f"- [ ] **{item['title']}**{when}, about {item['typical_minutes']} min. {item['why']}")
        lines += ["", f"Typical time if everything is done: about {total} minutes.", ""]
    return "\n".join(lines).rstrip() + "\n"
