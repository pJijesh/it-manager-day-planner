"""Build a time-blocked plan for one day. See docs/how-the-planner-works.md for the full model.

All times are integer minutes since midnight. Everything is deterministic: the same
profile, tasks, date and options always give the same plan, and every block carries a
plain-English reason.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from fractions import Fraction

from .model import Duty, Profile, Task
from .profile import meeting_applies
from .recurrence import describe_cadence, is_working_day, occurs_on
from .scoring import Score, score_task, sort_key
from .tasks import CLEARED_STATUSES
from .timeutil import fmt_time, long_date, short_date, weekday_key, weekday_name

Interval = tuple[int, int]

BUFFER_TITLE = "Interruptions and incidents"
BUFFER_ROUNDING_MINUTES = 5


# ---------------------------------------------------------------- interval helpers

def total(ivs: list[Interval]) -> int:
    return sum(e - s for s, e in ivs)


def overlap(a: Interval, b: Interval) -> int:
    return max(0, min(a[1], b[1]) - max(a[0], b[0]))


def subtract(ivs: list[Interval], cut: Interval) -> list[Interval]:
    out: list[Interval] = []
    for s, e in ivs:
        if cut[1] <= s or cut[0] >= e:
            out.append((s, e))
            continue
        if s < cut[0]:
            out.append((s, cut[0]))
        if cut[1] < e:
            out.append((cut[1], e))
    return out


def subtract_many(ivs: list[Interval], cuts: list[Interval]) -> list[Interval]:
    for cut in cuts:
        ivs = subtract(ivs, cut)
    return ivs


def intersect_window(ivs: list[Interval], window: Interval | None) -> list[Interval]:
    if window is None:
        return []
    out = []
    for s, e in ivs:
        lo, hi = max(s, window[0]), min(e, window[1])
        if lo < hi:
            out.append((lo, hi))
    return out


def merge(ivs: list[Interval]) -> list[Interval]:
    out: list[Interval] = []
    for s, e in sorted(ivs):
        if out and s <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], e))
        else:
            out.append((s, e))
    return out


# ---------------------------------------------------------------- result types

@dataclass
class Block:
    start: int
    end: int
    kind: str  # meeting, duty, lunch, buffer, task, free
    title: str
    reason: str = ""
    task_id: str | None = None
    category: str | None = None
    deep: bool = False
    part: str = ""  # for example "part 1 of 2"

    @property
    def minutes(self) -> int:
        return self.end - self.start

    @property
    def checkbox(self) -> bool:
        return self.kind in ("task", "duty")


@dataclass
class DayPlan:
    date: date
    working_day: bool
    hours: tuple[int, int] | None
    name: str
    organisation: str
    buffer_percent: float
    deep_window: tuple[int, int] | None
    min_block_minutes: int
    blocks: list[Block] = field(default_factory=list)
    not_today: list[dict] = field(default_factory=list)
    excluded: list[dict] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)
    capacity: dict = field(default_factory=dict)
    ignored_done: int = 0
    unplaced_duties: list[str] = field(default_factory=list)

    def task_blocks(self) -> list[Block]:
        return [b for b in self.blocks if b.kind == "task"]


# ---------------------------------------------------------------- small helpers

def round_buffer(working_minutes: int, percent: float) -> tuple[int, Fraction]:
    """Buffer minutes: percent of working time, rounded half up to the nearest 5 minutes.

    Returns (rounded minutes, exact value) using exact fractions so that halves round predictably.
    """
    exact = Fraction(working_minutes) * Fraction(str(percent)) / 100
    units = math.floor(exact / BUFFER_ROUNDING_MINUTES + Fraction(1, 2))
    return units * BUFFER_ROUNDING_MINUTES, exact


def _num(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{float(value):.2f}".rstrip("0").rstrip(".")


def _pct(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


def next_working_day(profile: Profile, day: date) -> date | None:
    current = day
    for _ in range(21):
        current += timedelta(days=1)
        if is_working_day(profile, current):
            return current
    return None


def _split_sizes(minutes: int, parts: int) -> list[int]:
    """Split minutes into parts, in multiples of 5 where possible, earlier parts larger."""
    units, rest = divmod(minutes, 5)
    q, r = divmod(units, parts)
    sizes = [(q + (1 if i < r else 0)) * 5 for i in range(parts)]
    sizes[-1] += rest
    return sizes


def _carve_buffer(pool: list[Interval], reserve: int, block_len: int, min_block: int) -> list[Interval]:
    """Choose the intervals that hold the buffer.

    The pool is the usable free time (sorted, separate intervals). The reserve is cut into
    m = ceil(reserve / block_len) parts. Part i is assigned to the interval that contains the
    point (2i + 1) x n / (2m) of the pool laid end to end, so the parts spread through the day
    in proportion to the free time. Each interval then gives up one block, taken from its END,
    because interruptions tend to land just before the next fixed commitment. If a block would
    leave a remainder shorter than the minimum block, the whole interval is taken and later
    blocks shrink to keep the total. Overflow moves on to the next interval.
    """
    if reserve <= 0 or not pool:
        return []
    n = total(pool)
    m = max(1, math.ceil(reserve / block_len))
    sizes = _split_sizes(reserve, m)
    starts, offset = [], 0
    for s, e in pool:
        starts.append(offset)
        offset += e - s
    want = [0] * len(pool)
    for i, size in enumerate(sizes):
        centre = ((2 * i + 1) * n) // (2 * m)
        j = max(k for k, st in enumerate(starts) if st <= centre)
        want[j] += size
    take = [0] * len(pool)
    carry = 0
    for j, (s, e) in enumerate(pool):
        length = e - s
        need = want[j] + carry
        if need <= 0:
            carry = need
            continue
        c = min(need, length)
        if 0 < length - c < min_block:
            c = length
        take[j] = c
        carry = need - c
    for j in range(len(pool) - 1, -1, -1):
        if carry <= 0:
            break
        s, e = pool[j]
        room = (e - s) - take[j]
        if room > 0:
            add = min(room, carry)
            if 0 < room - add < min_block:
                add = room
            take[j] += add
            carry -= add
    return [(e - t, e) for (s, e), t in zip(pool, take) if t > 0]


def _place_in_zone(zone: list[Interval], need: int, min_block: int) -> list[Interval]:
    """Pieces for a task inside one zone. Prefer a single block; otherwise split.

    Every piece is at least min_block long, except when the whole task is shorter than
    min_block, in which case it is a single block of its own length. A split never leaves
    a final piece shorter than min_block.
    """
    for s, e in zone:
        if e - s >= need:
            return [(s, s + need)]
    if need < 2 * min_block:
        return []  # too short to split into two blocks of at least min_block
    pieces: list[Interval] = []
    remaining = need
    for s, e in zone:
        if remaining == 0:
            break
        length = e - s
        if length >= remaining:
            piece = remaining
        else:
            piece = length
            if remaining - piece < min_block:
                piece = remaining - min_block
        if piece < min_block:
            continue
        pieces.append((s, s + piece))
        remaining -= piece
    return pieces


# ---------------------------------------------------------------- the planner

def plan_day(
    profile: Profile,
    tasks: list[Task],
    day: date,
    buffer_percent: float | None = None,
    remaining: dict[str, int] | None = None,
    assumed_done: dict[str, date] | None = None,
) -> DayPlan:
    """Plan one day.

    remaining: minutes still to schedule per task id (defaults to each task's estimate).
    assumed_done: task id to the date its last block is planned, used by the week planner so
    that a task whose blocker is planned earlier in the week can start.
    """
    pct = profile.buffer_percent if buffer_percent is None else buffer_percent
    remaining = dict(remaining or {})
    assumed_done = dict(assumed_done or {})
    plan = DayPlan(
        date=day, working_day=False, hours=None, name=profile.name, organisation=profile.organisation,
        buffer_percent=pct, deep_window=None, min_block_minutes=profile.min_block_minutes,
    )

    if not is_working_day(profile, day):
        why = ("it is listed in bank_holidays" if day in profile.bank_holidays
               else f"the profile has no working hours for {weekday_name(day)}")
        plan.warnings.append({"level": "info", "message": f"{long_date(day)} is not a working day: {why}. No plan was built."})
        plan.capacity = _capacity(0, 0, 0, 0, 0, pct, 0, 0, 0, 0, 0)
        return plan

    start_day, end_day = profile.hours[weekday_key(day)]
    plan.working_day = True
    plan.hours = (start_day, end_day)
    day_window = (start_day, end_day)
    min_block = profile.min_block_minutes

    lunch = None
    if profile.lunch is not None:
        lo, hi = max(profile.lunch[0], start_day), min(profile.lunch[1], end_day)
        if lo < hi:
            lunch = (lo, hi)
    lunch_minutes = (lunch[1] - lunch[0]) if lunch else 0
    working = (end_day - start_day) - lunch_minutes

    deep = None
    if profile.deep_window is not None:
        lo, hi = max(profile.deep_window[0], start_day), min(profile.deep_window[1], end_day)
        if lo < hi:
            deep = (lo, hi)
    plan.deep_window = deep

    if buffer_percent is not None and buffer_percent != profile.buffer_percent:
        plan.warnings.append({"level": "info", "message": (
            f"The interruption buffer is set to {_pct(pct)}% for this plan; the profile says {_pct(profile.buffer_percent)}%.")})

    # 1. Fixed meetings, clipped to working hours.
    meeting_blocks: list[Block] = []
    meeting_minutes = 0
    todays = sorted((m for m in profile.meetings if meeting_applies(m, day)), key=lambda m: (m.start, m.title))
    for m in todays:
        lo, hi = max(m.start, start_day), min(m.end, end_day)
        if lo >= hi:
            plan.warnings.append({"level": "warning", "message": (
                f"Meeting {m.title!r} ({fmt_time(m.start)} to {fmt_time(m.end)}) is outside working hours "
                f"({fmt_time(start_day)} to {fmt_time(end_day)}) and is left out of the plan.")})
            continue
        if (lo, hi) != (m.start, m.end):
            plan.warnings.append({"level": "warning", "message": (
                f"Meeting {m.title!r} ({fmt_time(m.start)} to {fmt_time(m.end)}) runs outside working hours. "
                "Only the part inside working hours is counted.")})
        in_lunch = overlap((lo, hi), lunch) if lunch else 0
        meeting_minutes += (hi - lo) - in_lunch
        reason = "Fixed meeting from the profile."
        if in_lunch:
            reason += f" It overlaps lunch by {in_lunch} minutes, so lunch is shortened."
            plan.warnings.append({"level": "warning", "message": (
                f"Meeting {m.title!r} overlaps lunch by {in_lunch} minutes. Lunch is shortened, and the "
                "overlap is not counted against working capacity.")})
        meeting_blocks.append(Block(lo, hi, "meeting", m.title, reason))
    busy = [(b.start, b.end) for b in meeting_blocks]
    lunch_pieces = subtract_many([lunch], busy) if lunch else []
    lunch_blocks = []
    for s, e in lunch_pieces:
        lunch_blocks.append(Block(s, e, "lunch", "Lunch", "Protected break from the profile."))
    if lunch and total(lunch_pieces) == 0:
        plan.warnings.append({"level": "warning", "message": "Meetings cover the whole lunch break, so there is no lunch today."})

    free = subtract_many([day_window], busy + [lunch] if lunch else busy)
    free = merge(free)

    # 2. Recurring duties.
    duties_today = [d for d in profile.duties if occurs_on(profile, d, day)]
    duty_minutes_required = sum(d.minutes for d in duties_today)
    ordered = sorted(
        enumerate(duties_today),
        key=lambda p: (p[1].preferred_start is None, p[1].preferred_start or 0, p[0]),
    )
    duty_blocks: list[Block] = []
    for _, duty in ordered:
        placed = _place_duty(free, duty)
        if placed is None:
            plan.unplaced_duties.append(duty.title)
            plan.warnings.append({"level": "alert", "message": (
                f"Recurring duty {duty.title!r} ({duty.minutes} min) could not be placed: no free gap of that "
                "length is left after meetings and other duties. Move it by hand or shorten a meeting.")})
            continue
        (s, e), how = placed
        free = subtract(free, (s, e))
        duty_blocks.append(Block(s, e, "duty", duty.title, f"Recurring duty, {describe_cadence(duty)}. {how}", category="duty"))
    duty_minutes = sum(b.minutes for b in duty_blocks)

    # 3. Capacity warnings that depend only on fixed commitments.
    commitments = meeting_minutes + duty_minutes_required
    buffer_target, exact = round_buffer(working, pct)
    if commitments > working:
        plan.warnings.append({"level": "alert", "message": (
            f"OVERLOADED: fixed commitments exceed the working day. Meetings take {meeting_minutes} min and "
            f"recurring duties {duty_minutes_required} min, together {commitments} min, but the working day has "
            f"{working} min (lunch excluded). Over by {commitments - working} min. Renegotiate, delegate or move "
            "something before planning any tasks.")})
    elif working - commitments - buffer_target <= 0:
        plan.warnings.append({"level": "warning", "message": (
            f"No room for tasks: meetings and duties take {commitments} of {working} min, leaving "
            f"{working - commitments} min, which is not more than the {buffer_target} min protected buffer. "
            "No tasks are planned today. Free some time or lower the buffer for a day on purpose.")})

    free_after_fixed = list(free)

    # 4. Gaps too short for a task count as buffer, then reserve the rest of the buffer.
    slivers = [iv for iv in free if iv[1] - iv[0] < min_block]
    usable = [iv for iv in free if iv[1] - iv[0] >= min_block]
    sliver_minutes = total(slivers)
    reserve = max(0, buffer_target - sliver_minutes)
    reserve = min(reserve, total(usable))
    outside_deep = merge(subtract(usable, deep)) if deep else usable
    if total(outside_deep) >= reserve:
        pool, where = outside_deep, "kept outside the deep-work window"
    else:
        pool, where = usable, "spread across all free time because there is too little free time outside the deep-work window"
        if not deep:
            where = "spread across the day's free time"
    buffer_ivs = _carve_buffer(pool, reserve, profile.buffer_block_minutes, min_block)
    free = merge(subtract_many(usable, buffer_ivs))
    # Leftovers beside a buffer block that are too short for a task also become buffer.
    post_slivers = [iv for iv in free if iv[1] - iv[0] < min_block]
    free = [iv for iv in free if iv[1] - iv[0] >= min_block]

    exact_text = _num(exact)
    base_reason = (f"Protected buffer: {_pct(pct)}% of {working} working minutes is {exact_text}, "
                   f"rounded to {buffer_target} minutes; {where}.")
    buffer_blocks = [Block(s, e, "buffer", BUFFER_TITLE, base_reason) for s, e in merge(buffer_ivs)]
    for s, e in slivers + post_slivers:
        buffer_blocks.append(Block(s, e, "buffer", BUFFER_TITLE,
                                   f"A gap of {e - s} minutes is shorter than the {min_block} minute minimum block, "
                                   "so it is counted as buffer."))
    buffer_blocks = _coalesce_buffer(buffer_blocks)
    buffer_minutes = sum(b.minutes for b in buffer_blocks)

    # 5. Eligibility and scoring.
    eligible: list[tuple[Task, Score]] = []
    cleared = {t.id for t in tasks if t.status in CLEARED_STATUSES}
    by_id = {t.id: t for t in tasks}
    for task in tasks:
        if task.status in CLEARED_STATUSES:
            plan.ignored_done += 1
            continue
        reasons = []
        available_from = None
        if task.status == "waiting":
            reasons.append("Status is waiting: it depends on someone else, so there is nothing to schedule yet.")
        open_blockers = [b for b in task.blocked_by if b not in cleared and not (b in assumed_done and assumed_done[b] < day)]
        if open_blockers:
            text = ", ".join(f"{b} ({by_id[b].status})" for b in open_blockers)
            reasons.append(f"Blocked by {text}.")
        if task.earliest_start and task.earliest_start > day:
            reasons.append(f"Not startable until {task.earliest_start.isoformat()}.")
            available_from = task.earliest_start.isoformat()
        if reasons:
            plan.excluded.append({"id": task.id, "title": task.title, "reason": " ".join(reasons), "available_from": available_from})
            continue
        if remaining.get(task.id, task.estimate_minutes) <= 0:
            continue
        eligible.append((task, score_task(task, day)))
    eligible.sort(key=lambda p: sort_key(*p))

    # 6. Place tasks. Deep tasks use the deep window first. Other tasks stay outside it in the first
    # pass, and may use whatever is left of the window in the second pass.
    pieces: dict[str, list[tuple[Interval, str]]] = {t.id: [] for t, _ in eligible}
    need_left = {t.id: remaining.get(t.id, t.estimate_minutes) for t, _ in eligible}
    original_need = dict(need_left)
    for task, _ in eligible:
        zones = ["deep", "out"] if task.category.lower() == "deep" else ["out"]
        _take(task, zones, free, deep, min_block, need_left, pieces)
    for task, _ in eligible:
        if need_left[task.id] > 0 and task.category.lower() != "deep":
            _take(task, ["deep"], free, deep, min_block, need_left, pieces)

    task_blocks: list[Block] = []
    for task, score in eligible:
        got = sorted(pieces[task.id])
        n = len(got)
        is_deep = task.category.lower() == "deep"
        for i, ((s, e), zone) in enumerate(got, 1):
            reason = score.explain() + ". " + _task_reason(task, is_deep, zone, deep, assumed_done, day, by_id)
            if n > 1:
                reason += f" Split into {n} blocks (none shorter than {min_block} minutes) because no single free gap was long enough."
            task_blocks.append(Block(s, e, "task", task.title, reason, task_id=task.id, category=task.category,
                                     deep=is_deep, part=f"part {i} of {n}" if n > 1 else ""))

    # 7. Not today.
    suggested = next_working_day(profile, day)
    for task, score in eligible:
        left = need_left[task.id]
        if left <= 0:
            continue
        placed = original_need[task.id] - left
        if placed:
            reason = (f"Only {placed} of {original_need[task.id]} minutes fit. The other {left} minutes found no time "
                      "after meetings, duties, the buffer and higher-scoring tasks.")
        elif total(free) == 0:
            reason = "No time left after meetings, duties, the buffer and higher-scoring tasks."
        else:
            largest = max(e - s for s, e in free)
            reason = (f"The largest free gap left is {largest} minutes. It needs {original_need[task.id]}, "
                      f"and blocks are never shorter than {min_block} minutes.")
        note = ""
        if task.due is not None and task.due <= day:
            note = ("Already overdue: renegotiate the date, delegate it or drop it, rather than letting it slide again."
                    if task.due < day else
                    "Due today but not placed: renegotiate the date or delegate it today.")
        plan.not_today.append({
            "id": task.id, "title": task.title, "minutes_needed": original_need[task.id], "minutes_placed": placed,
            "score": score.total, "reason": reason,
            "suggested_day": suggested.isoformat() if suggested else None,
            "note": note,
        })

    # 8. Anything left is free, unplanned time.
    free_blocks = [Block(s, e, "free", "Free, unplanned", "Left over: no remaining task fits this gap.")
                   for s, e in merge(free)]
    if deep and any(t.category.lower() == "deep" for t, _ in eligible):
        deep_free = total(intersect_window(free_after_fixed, deep))
        if deep_free < min_block:
            plan.warnings.append({"level": "warning", "message": (
                f"The deep-work window ({fmt_time(deep[0])} to {fmt_time(deep[1])}) has only {deep_free} minutes "
                "left after meetings and duties, so deep tasks will land outside it. Consider moving a meeting.")})

    blocks = meeting_blocks + lunch_blocks + duty_blocks + buffer_blocks + task_blocks + free_blocks
    blocks.sort(key=lambda b: (b.start, b.end, b.kind, b.title))
    plan.blocks = blocks
    tasks_planned = sum(b.minutes for b in task_blocks)
    free_minutes = sum(b.minutes for b in free_blocks)
    plan.capacity = _capacity(working, lunch_minutes, meeting_minutes, duty_minutes, duty_minutes_required, pct,
                              buffer_target, buffer_minutes, tasks_planned, free_minutes, commitments)
    return plan


def _capacity(working, lunch, meetings, duties, duties_required, pct, target, buffer, tasks, free, commitments) -> dict:
    return {
        "working_minutes": working,
        "lunch_minutes": lunch,
        "meeting_minutes": meetings,
        "duty_minutes": duties,
        "duty_minutes_required": duties_required,
        "fixed_commitment_minutes": commitments,
        "buffer_percent": pct,
        "buffer_target_minutes": target,
        "buffer_minutes": buffer,
        "task_minutes_planned": tasks,
        "free_minutes": free,
        "task_capacity_minutes": tasks + free,
    }


def _coalesce_buffer(blocks: list[Block]) -> list[Block]:
    """Join buffer blocks that touch, keeping the main reason and noting any short gaps absorbed."""
    blocks = sorted(blocks, key=lambda b: (b.start, b.end))
    out: list[Block] = []
    for b in blocks:
        if out and out[-1].end == b.start:
            prev = out[-1]
            main = prev.reason if prev.reason.startswith("Protected") else b.reason
            extra = b if not b.reason.startswith("Protected") else prev
            note = ""
            if not extra.reason.startswith("Protected"):
                note = f" It also absorbs a {extra.minutes} minute gap too short for a task."
            out[-1] = Block(prev.start, b.end, "buffer", BUFFER_TITLE, main + note)
        else:
            out.append(b)
    return out


def _place_duty(free: list[Interval], duty: Duty) -> tuple[Interval, str] | None:
    m = duty.minutes
    pref = duty.preferred_start
    if pref is not None:
        for s, e in free:
            if s <= pref and pref + m <= e:
                return (pref, pref + m), f"Placed at its preferred start, {fmt_time(pref)}."
        for s, e in free:
            start = max(s, pref)
            if start + m <= e:
                return (start, start + m), f"Preferred start {fmt_time(pref)} was not free, so it is placed at {fmt_time(start)}."
    if pref is not None:
        for s, e in reversed(free):  # nothing at or after the preferred start: the latest start before it
            start = min(e - m, pref)
            if start >= s:
                return (start, start + m), f"Nothing free at or after {fmt_time(pref)}, so it is placed at the latest time before it that fits, {fmt_time(start)}."
    else:
        for s, e in free:
            if e - s >= m:
                return (s, s + m), "No preferred start, so it takes the first free gap."
    return None


def _take(task: Task, zones: list[str], free: list[Interval], deep: Interval | None, min_block: int,
          need_left: dict[str, int], pieces: dict) -> None:
    """Place as much of the task as possible, zone by zone. Mutates free, need_left and pieces."""
    for zone in zones:
        if need_left[task.id] <= 0:
            return
        if zone == "deep":
            zone_ivs = intersect_window(free, deep)
        else:
            zone_ivs = merge(subtract(free, deep)) if deep else list(free)
        got = _place_in_zone(zone_ivs, need_left[task.id], min_block)
        for iv in got:
            free[:] = subtract(free, iv)
            pieces[task.id].append((iv, zone))
            need_left[task.id] -= iv[1] - iv[0]


def _task_reason(task: Task, is_deep: bool, zone: str, deep: Interval | None, assumed_done: dict, day: date, by_id: dict) -> str:
    if deep is None:
        text = "Placed in the earliest free time that fits."
    elif is_deep and zone == "deep":
        text = f"Deep-work task, placed in the deep-work window ({fmt_time(deep[0])} to {fmt_time(deep[1])})."
    elif is_deep:
        text = "Deep-work task, but the deep-work window had no suitable free time left, so it sits outside it."
    elif zone == "out":
        text = "Placed outside the deep-work window, which is kept for deep tasks."
    else:
        text = "Placed in the deep-work window because no other free time was left and no deep task needed it."
    early = [b for b in task.blocked_by if b in assumed_done and assumed_done[b] < day and by_id[b].status not in CLEARED_STATUSES]
    if early:
        text += " It assumes " + ", ".join(f"{b} (planned to finish {short_date(assumed_done[b])})" for b in early) + " is done."
    return text
