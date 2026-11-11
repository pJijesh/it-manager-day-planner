"""Write docs/operating-rhythm.md from data/operating-rhythm.json so the two never drift apart.

Run from the repository root:  python scripts/build_rhythm_doc.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from day_planner.rhythm import load_rhythm  # noqa: E402

HEAD = """# Operating rhythm for an IT manager

{note}

This page is generated from [`data/operating-rhythm.json`](../data/operating-rhythm.json). Print it with `day-planner rhythm`, or one cadence at a time with `--cadence weekly`.

## How to use it

1. Read each list once and delete what does not apply to you. A small organisation may fold several items into one.
2. Change the minutes to match how long the task really takes in your environment.
3. Copy the items you keep into `recurring_duties` in your profile, using the cadence that matches (daily, weekly, monthly on a day or on the last working day, quarterly or annual). The planner then places them in the day for you. [How the planner works](how-the-planner-works.md) explains the cadence options.
4. Review the list every quarter. Drop items that never find anything, and add the ones that would have caught your last surprise.

## What this is not

- It is not a standard, a framework or a compliance checklist.
- The frequencies are practitioner suggestions. This repository does not state that any law, regulation, contract or standard requires a particular frequency for any item. Where a rule applies to you (a regulator, a customer contract, an insurer, a certification scheme), follow that source and the frequency it gives, and record that in your own list.
- The minutes are typical figures for a small or mid-size organisation, not benchmarks.

"""

FOOT = """
## Linking the rhythm to the day plan

The daily items fit before the deep-work window and after lunch, so they are cheap when done in the same place every day. The weekly and monthly items work best at a fixed weekday so that people know when to expect them. Quarterly and annual items are the ones that get missed: put them in the diary as recurring duties with a month and a day rule, and rebuild the contract and certificate calendar once a year.

See also the [templates](../templates/) for the weekly review, the monthly leadership update and the shutdown checklist, and [time blocking for IT managers](time-blocking-for-it-managers.md).
"""


def build() -> str:
    data = load_rhythm(ROOT / "data" / "operating-rhythm.json")
    out = [HEAD.format(note=data["note"])]
    for block in data["cadences"]:
        items = block["items"]
        out.append(f"## {block['label']}\n")
        if block.get("intro"):
            out.append(block["intro"] + "\n")
        out.append("| ID | Item | Why it is on the list | Typical minutes | Suggested when |")
        out.append("|---|---|---|---|---|")
        for item in items:
            when = item.get("suggested_when", "")
            out.append(f"| {item['id']} | {item['title']} | {item['why']} | {item['typical_minutes']} | {when} |")
        out.append("")
    out.append(FOOT)
    return "\n".join(out).rstrip() + "\n"


if __name__ == "__main__":
    (ROOT / "docs" / "operating-rhythm.md").write_text(build(), encoding="utf-8", newline="\n")
