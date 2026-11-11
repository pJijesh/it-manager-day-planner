# Getting started

This takes about fifteen minutes. You need Python 3.10 or later. There is nothing to install except the tool itself, and no account or network connection.

## 1. Get the tool

```bash
git clone https://github.com/pJijesh/it-manager-day-planner.git
cd it-manager-day-planner
pip install -e .        # optional: adds the day-planner command
```

Without installing, `python -m day_planner` works from the repository folder.

## 2. Create your workspace

```bash
python -m day_planner init my-planner
```

This writes `profile.json`, `tasks.csv` and a short `README.md` into `my-planner/`. Existing files are never overwritten unless you pass `--force`.

## 3. Edit the profile

Open `my-planner/profile.json` and change, in this order:

1. `working_hours` and `lunch` to match your real day.
2. `fixed_meetings`: the meetings you cannot move. Use `weekday` or `weekdays` for regular ones and `date` for one-offs.
3. `deep_work_window`: the part of the day when you do your best thinking.
4. `recurring_duties`: your daily and weekly checks. [The operating rhythm](operating-rhythm.md) lists candidates, and `python -m day_planner rhythm` prints them.
5. `bank_holidays`: add the dates that apply to you, taken from your official list. Nothing is looked up online.
6. `buffer_percent`: start at 30 and adjust after a few weeks.

The full field list and the exact rules are in [how the planner works](how-the-planner-works.md). A mistake gives a message that says which field and what to do, and the tool lists every problem in one go.

## 4. Edit the task list

`tasks.csv` needs `id`, `title` and `estimate_minutes`. Everything else is optional. Use `deep` as the category for work that needs focus, `blocked_by` for dependencies (task ids separated by semicolons) and `earliest_start` for work that cannot begin yet. Estimates are your own; round up.

## 5. Plan a day

```bash
cd my-planner
python -m day_planner plan --profile profile.json --tasks tasks.csv --date 2026-10-26
python -m day_planner plan --profile profile.json --tasks tasks.csv --date 2026-10-26 --format html --out plan.html
```

Open `plan.html` in a browser and print it on A4, or save it as a PDF. It uses no JavaScript. Read the **Not today** list and the warnings first: they are the part that needs a decision.

## 6. Plan the week and review it

```bash
python -m day_planner week   --profile profile.json --tasks tasks.csv --start 2026-10-26
python -m day_planner review --profile profile.json --tasks tasks.csv --week-start 2026-10-26
```

`week` needs a Monday. Add `--daily` to include each day's full plan. For the review, record `completed` dates (and `actual_minutes` if you like) on finished tasks.

## 7. Use the templates

The [templates](../templates/) folder has printable Markdown for the daily plan, shutdown checklist, weekly review, one-to-ones, decision log, incident handover and the monthly leadership update. Copy what you use.

## Try the worked example first

The [`examples/`](../examples/) folder holds a fictional organisation, a profile, a task list and every output format. Running the commands in the [README](../README.md) on it will reproduce those files exactly.

## Limits to keep in mind

The tool reads two local files and writes only what you ask for. It does not talk to a calendar or ticketing system, so keeping the files up to date is your job. The plan is only as good as your estimates, and the rhythm is generic, so adapt it.
