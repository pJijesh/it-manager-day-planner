# Operating rhythm for an IT manager

These are practitioner suggestions to adapt to your organisation, its size, its risks and its contracts. They are not standards. No frequency or duration here is stated or required by any law, regulation or standard. Where a contract, regulator or certification scheme applies to you, follow that source and the frequency it gives.

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


## Daily

A short routine that finds problems while they are small. About 80 minutes in total, much of it in the first hour of the day.

| ID | Item | Why it is on the list | Typical minutes | Suggested when |
|---|---|---|---|---|
| D01 | Overnight alerts and backup results | A failed backup or a quiet alert channel is easy to miss. Read the job results instead of assuming they ran. | 15 | start of day |
| D02 | Service desk queue and SLA breaches | Look at the oldest tickets, anything breached or about to breach, and who is stuck. Ageing tickets are where users lose trust. | 15 | start of day |
| D03 | Security alerts and unusual sign-ins | Check the security console or alert digest for anything that needs a decision, such as a new admin account or repeated failed sign-ins. | 10 | start of day |
| D04 | Change calendar for today and tomorrow | Know what is changing, who owns it and whether it collides with a busy business period. Stop or move a change that is not ready. | 10 | before mid-morning |
| D05 | Expiring certificates, licences and domains | A glance at the list of items expiring in the next 30 days. Expiry outages are avoidable and embarrassing. | 5 | start of day |
| D06 | People check-ins | A few short conversations or messages: who is blocked, who is overloaded, who is out. Fix small blockers the same day. | 10 | after stand-up |
| D07 | Set the top three for the day | Pick the three results that would make today a good day, and say what will not happen. Use the day plan to check they fit. | 5 | start of day |
| D08 | End-of-day shutdown | Capture loose ends, update the task list, note handover points and set tomorrow's first task. See templates/end-of-day-shutdown.md. | 10 | end of day |

## Weekly

Where priorities, people and spend are kept in line. Roughly four to six hours a week, mostly meetings you already have.

| ID | Item | Why it is on the list | Typical minutes | Suggested when |
|---|---|---|---|---|
| W01 | IT team meeting | Share priorities, incidents and changes, and agree who owns what. Keep it short and decision-led. | 30 | early in the week |
| W02 | One-to-ones with direct reports (per person) | Regular, protected time for each person: workload, blockers, development and how they are. Cancelling them teaches the team what matters least. | 30 | spread across the week |
| W03 | Vendor actions and chasing | Review open supplier tickets, quotes and deliveries. Chase the ones that are late and record the answer. | 30 | mid-week |
| W04 | Risk register review | Check new risks, changed ratings and overdue actions. Close or escalate, do not just re-read. | 30 | mid-week |
| W05 | Budget and spend check | Compare committed and actual spend with the budget line by line for anything unusual, new subscriptions and unapproved purchases. | 20 | mid-week |
| W06 | Patch and vulnerability status | How many devices and servers are behind, what is overdue, and what exceptions are open. Decide what is pushed this week. | 30 | mid-week |
| W07 | Projects and change review | Status of live projects, upcoming changes and anything that needs a decision or more people. | 30 | mid-week |
| W08 | Backlog tidy | Close stale tasks, split large ones, re-rate importance and make sure blocked items have an owner. See docs/time-blocking-for-it-managers.md. | 30 | end of week |
| W09 | Weekly review and next week's plan | Look at what was done, what rolled over and what is overdue, then plan next week. See templates/weekly-review.md. | 30 | end of week |

## Monthly

Evidence, reporting and checks that something still works. Roughly eight hours a month.

| ID | Item | Why it is on the list | Typical minutes | Suggested when |
|---|---|---|---|---|
| M01 | KPI pack | Collect the handful of measures you track (for example availability, ticket volumes, SLA performance, patching and spend) and note what changed and why. | 90 | last week of the month |
| M02 | Board or leadership report | A one to two page update: what happened, what is at risk, what you need decided. See templates/monthly-leadership-update.md. | 90 | last working days of the month |
| M03 | Access review sample | Pick a sample of accounts and permissions, especially administrators, and confirm each is still needed. Record what you removed. | 45 | mid-month |
| M04 | Licence and subscription review | Match paid licences and subscriptions to people and use. Reclaim or cancel what is idle. | 45 | mid-month |
| M05 | Backup restore or DR test | Restore a real item from backup, or run one step of the recovery plan, and write down how long it took and what broke. A backup that has not been restored is a hope. | 60 | mid-month |
| M06 | Budget forecast against actuals | Update the year-end forecast and explain variances to the finance partner before they ask. | 60 | after month end |
| M07 | Joiners, movers and leavers reconciliation | Compare the HR list of leavers and movers with accounts, devices and licences. Close the gaps. | 30 | after month end |
| M08 | Incident and problem review | Look for repeat incidents and near misses. Pick one cause to remove. | 45 | after month end |

## Quarterly

Bigger conversations that need preparation. Roughly ten hours a quarter, more if you have several key suppliers to review.

| ID | Item | Why it is on the list | Typical minutes | Suggested when |
|---|---|---|---|---|
| Q01 | Supplier reviews (key suppliers) | Review service, cost, risks and relationship with each key supplier, and agree actions. Do this before renewal dates, not after. | 60 | before renewal windows |
| Q02 | Policy review | Review a rotating share of IT policies so each one is read at least once a year. Retire the ones nobody follows. | 60 | first month of the quarter |
| Q03 | Tabletop exercise | Walk the team through a realistic incident on paper: who does what, who is told and what decisions are needed. Record the gaps and fix them. | 120 | once a quarter |
| Q04 | Roadmap and priorities review | Check progress against the plan, drop what no longer matters and confirm the next quarter's priorities with leadership. | 90 | start of the quarter |
| Q05 | Full risk register review | Rework the whole register with owners: ratings, treatments, accepted risks and new risks. | 60 | mid-quarter |
| Q06 | Privileged access review | Review all administrator and service accounts and their owners, not just a sample. | 90 | mid-quarter |
| Q07 | Lifecycle and capacity review | List hardware and software nearing end of support, and storage, network and licence headroom. Feed the budget. | 60 | end of the quarter |
| Q08 | Team development check | Review objectives, training, workload and succession for each role. | 60 | end of the quarter |

## Annual

Large pieces of work that need to be put in the diary months ahead.

| ID | Item | Why it is on the list | Typical minutes | Suggested when |
|---|---|---|---|---|
| A01 | Budget cycle | Prepare the next year's operating and project budget with evidence from the lifecycle review and the roadmap. Total effort, spread over several weeks. | 480 | ahead of your finance deadline |
| A02 | Contract renewals calendar | Rebuild the list of every supplier contract with end date, notice period and owner, and set reminders well before each notice date. | 120 | once a year, then keep current |
| A03 | Full disaster recovery test | Run a complete recovery of a priority service in a safe way, time it and compare it with what the business expects. Total effort including preparation. | 240 | once a year |
| A04 | Certification and accreditation renewals | List every certificate, accreditation, training record and assurance report that expires, with the lead time to renew it. | 60 | once a year, then keep current |
| A05 | Strategy and roadmap refresh | Revisit the multi-year direction with leadership. Check it still fits where the business is going. | 240 | once a year |
| A06 | Third-party assurance requests | Ask critical suppliers for current evidence of how they protect your data and keep service running, and note what is missing. | 90 | once a year |
| A07 | Team training and succession plan | Agree development plans, cover for key people and the skills you need next year. | 90 | once a year |


## Linking the rhythm to the day plan

The daily items fit before the deep-work window and after lunch, so they are cheap when done in the same place every day. The weekly and monthly items work best at a fixed weekday so that people know when to expect them. Quarterly and annual items are the ones that get missed: put them in the diary as recurring duties with a month and a day rule, and rebuild the contract and certificate calendar once a year.

See also the [templates](../templates/) for the weekly review, the monthly leadership update and the shutdown checklist, and [time blocking for IT managers](time-blocking-for-it-managers.md).
