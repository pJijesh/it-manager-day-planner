# Worked example

Everything here is fictional. "Ottermere Fabrications Ltd" and its IT manager "Priya Calderbeck" are invented, and any resemblance to a real business or person is accidental. The task list and meetings are made up to show the planner's behaviour and are not benchmarks. The bank holidays in the profile are the England and Wales dates for 2026 from the GOV.UK list.

## Inputs

- [`profile.json`](profile.json): Monday to Thursday 08:30 to 17:30, Friday to 16:30, lunch 12:30 to 13:15, a 30 percent buffer, a deep-work window of 09:15 to 11:30, ten fixed meetings and fifteen recurring duties.
- [`tasks.csv`](tasks.csv): 26 tasks as they stand on the Monday morning. Five are not plannable on that Monday: T-03 (blocked by T-12), T-12 (waiting), T-14 (blocked by T-15), T-17 (not startable before 2 November) and T-25 (blocked by T-18). T-06 and T-07 are overdue. Five tasks are `deep`. T-26 is already done.
- [`tasks-friday-snapshot.csv`](tasks-friday-snapshot.csv): the same list on the Friday afternoon, with completion dates and actual minutes, used for the weekly review.

## Outputs, in `output/` as Markdown, HTML and JSON

| File stem | What it shows |
|---|---|
| `plan-monday` | A normal Monday (26 October 2026): leadership meeting at 14:00, one weekly duty, 30 percent buffer. |
| `plan-incident-day` | Tuesday 27 October with `--buffer 50`, the way to plan a day you expect to be eaten by an incident. Task time falls from 180 to 65 minutes and most of the list moves to Not today. |
| `plan-friday-month-end` | Friday 30 October, the last working day of October: the month-end KPI pack duty, an auditor walkthrough, a weekly review and a task due today that does not fully fit. |
| `week-overview` | Monday to Friday in one table, with flags, tasks by day, what is not scheduled this week and what is excluded. |
| `weekly-review` | The review sheet for that week (Markdown and JSON only), from the Friday snapshot. |

Regenerate all of them with `python scripts/regenerate_examples.py`. The tests compare a fresh run with these files byte for byte.
