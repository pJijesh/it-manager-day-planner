"""Blocked tasks, earliest start, deep work, splitting and overflow."""

from datetime import date

from day_planner.scheduler import _place_in_zone, plan_day
from helpers import profile, spans, tasks

MON = date(2026, 10, 26)


def simple_profile(**kw):
    """09:00 to 13:00, no lunch, no buffer: 240 free minutes unless a test says otherwise."""
    base = dict(working_hours={d: ["09:00", "13:00"] for d in ("mon", "tue", "wed", "thu", "fri")},
                lunch=None, buffer_percent=0)
    base.update(kw)
    return profile(**base)


# ---------------------------------------------------------------- eligibility

def test_blocked_task_is_excluded_with_the_blocker_named():
    t = tasks("A,Write,60,admin,,3,todo,,,\nB,Review,30,admin,,5,todo,A,,")
    plan = simple_profile() and plan_day(simple_profile(), t, MON)
    assert [b.task_id for b in plan.task_blocks()] == ["A"]
    assert plan.excluded == [{"id": "B", "title": "Review", "reason": "Blocked by A (todo).", "available_from": None}]


def test_done_blocker_does_not_block_and_cancelled_does_not_either():
    t = tasks("A,Write,60,admin,,3,done,,,\nB,Review,30,admin,,5,todo,A,,\nC,Old,30,admin,,3,cancelled,,,\nD,Next,30,admin,,3,todo,C,,")
    plan = plan_day(simple_profile(), t, MON)
    assert sorted(b.task_id for b in plan.task_blocks()) == ["B", "D"]
    assert plan.excluded == [] and plan.ignored_done == 2


def test_waiting_status_is_excluded():
    t = tasks("A,Chase,30,admin,,3,waiting,,,")
    plan = plan_day(simple_profile(), t, MON)
    assert plan.task_blocks() == []
    assert "waiting" in plan.excluded[0]["reason"]


def test_earliest_start_excludes_until_the_date():
    t = tasks("A,Later,30,admin,,3,todo,,2026-10-28,")
    plan = plan_day(simple_profile(), t, MON)
    assert plan.excluded[0]["reason"] == "Not startable until 2026-10-28."
    assert plan.excluded[0]["available_from"] == "2026-10-28"
    assert [b.task_id for b in plan_day(simple_profile(), t, date(2026, 10, 28)).task_blocks()] == ["A"]


def test_blocked_and_early_start_give_both_reasons():
    t = tasks("A,Dep,30,admin,,3,todo,,,\nB,Both,30,admin,,3,todo,A,2026-11-02,")
    plan = plan_day(simple_profile(), t, MON)
    assert "Blocked by A (todo)." in plan.excluded[0]["reason"]
    assert "Not startable until 2026-11-02." in plan.excluded[0]["reason"]


# ---------------------------------------------------------------- placement

def test_tasks_are_placed_in_score_order_earliest_first():
    t = tasks("LOW,Low,60,admin,,1,todo,,,\nHIGH,High,60,admin,,5,todo,,,")
    plan = plan_day(simple_profile(), t, MON)
    assert [(b.task_id, b.start) for b in plan.task_blocks()] == [("HIGH", 540), ("LOW", 600)]


def test_deep_task_uses_the_deep_window_and_others_stay_out_of_it():
    p = simple_profile(deep_work_window={"start": "09:00", "end": "11:00"})
    t = tasks("S,Shallow,60,admin,,5,todo,,,\nD,Deep,90,deep,,1,todo,,,")
    plan = plan_day(p, t, MON)
    placed = {b.task_id: (b.start, b.end) for b in plan.task_blocks()}
    assert placed["D"] == (540, 630)  # the window, even though the shallow task scores higher
    assert placed["S"] == (660, 720)  # outside the window (11:00 to 13:00)
    assert "deep-work window (09:00 to 11:00)" in [b for b in plan.task_blocks() if b.task_id == "D"][0].reason


def test_leftover_deep_window_is_released_to_other_tasks():
    p = simple_profile(deep_work_window={"start": "09:00", "end": "11:00"})
    t = tasks("S1,One,120,admin,,5,todo,,,\nS2,Two,60,admin,,4,todo,,,")  # no deep tasks at all
    plan = plan_day(p, t, MON)
    placed = {b.task_id: (b.start, b.end) for b in plan.task_blocks()}
    assert placed["S1"] == (660, 780)  # 11:00 to 13:00 outside the window
    assert placed["S2"] == (540, 600)  # second pass: the unused window
    assert "no deep task needed it" in [b for b in plan.task_blocks() if b.task_id == "S2"][0].reason


def test_deep_task_spills_outside_the_window_when_it_is_too_short():
    p = simple_profile(deep_work_window={"start": "09:00", "end": "10:00"},
                       fixed_meetings=[{"title": "M", "weekday": "mon", "start": "09:30", "end": "10:00"}])
    t = tasks("D,Deep,120,deep,,3,todo,,,")
    plan = plan_day(p, t, MON)
    blocks = plan.task_blocks()
    assert [(b.start, b.end) for b in blocks] == [(540, 570), (600, 690)]
    assert blocks[0].part == "part 1 of 2" and blocks[1].part == "part 2 of 2"
    assert "sits outside it" in blocks[1].reason


def test_long_task_is_split_across_gaps_with_no_piece_below_the_minimum():
    # Gaps 09:00-10:00 (60) and 11:00-13:00 (120). A 150 minute task fits neither whole.
    p = simple_profile(fixed_meetings=[{"title": "M", "weekday": "mon", "start": "10:00", "end": "11:00"}])
    plan = plan_day(p, tasks("A,Long,150,admin,,3,todo,,,"), MON)
    assert spans(plan, "task") == [("09:00", "10:00"), ("11:00", "12:30")]
    assert all(b.minutes >= 30 for b in plan.task_blocks())
    assert "Split into 2 blocks" in plan.task_blocks()[0].reason


def test_whole_fit_beats_splitting_and_takes_the_earliest_gap_that_holds_it():
    p = simple_profile(fixed_meetings=[{"title": "M", "weekday": "mon", "start": "10:00", "end": "11:00"}])
    plan = plan_day(p, tasks("A,Mid,90,admin,,3,todo,,,"), MON)
    assert spans(plan, "task") == [("11:00", "12:30")]  # the morning gap is only 60


def test_place_in_zone_split_never_leaves_a_stub():
    # Gaps of 100 and 90, task of 110, minimum 30: taking all 100 would leave 10, so take 80 and then 30.
    assert _place_in_zone([(540, 640), (700, 790)], 110, 30) == [(540, 620), (700, 730)]
    # 50 minutes is under twice the minimum, so it is never split.
    assert _place_in_zone([(0, 30), (100, 130)], 50, 30) == []
    # A task shorter than the minimum is placed whole in a gap that holds it.
    assert _place_in_zone([(0, 30)], 20, 30) == [(0, 20)]
    # A split can use three gaps: 40, then 30 (leaving 30 rather than a stub of 20), then 30.
    assert _place_in_zone([(0, 40), (100, 140), (200, 240)], 100, 30) == [(0, 40), (100, 130), (200, 230)]


def test_place_in_zone_pieces_always_respect_the_minimum():
    zones = [[(0, 45), (60, 100), (130, 200)], [(0, 31), (50, 81)], [(0, 35), (40, 120), (150, 190)]]
    for zone in zones:
        for need in range(35, 260, 7):
            pieces = _place_in_zone(zone, need, 30)
            assert all(e - s >= 30 for s, e in pieces)
            assert sum(e - s for s, e in pieces) <= need
            for (s, e), gap in zip(pieces, [g for g in zone if any(g[0] <= s < g[1] for s, _ in pieces)]):
                assert gap[0] <= s and e <= gap[1]


# ---------------------------------------------------------------- overflow and Not today

def test_task_that_does_not_fit_goes_to_not_today_with_reason_and_next_day():
    t = tasks("A,Big,300,admin,,3,todo,,,")
    plan = plan_day(simple_profile(), t, date(2026, 10, 30))  # Friday: 240 free minutes
    assert plan.task_blocks()[0].minutes == 240
    entry = plan.not_today[0]
    assert (entry["id"], entry["minutes_needed"], entry["minutes_placed"]) == ("A", 300, 240)
    assert entry["suggested_day"] == "2026-11-02"  # the next working day skips the weekend
    assert "Only 240 of 300 minutes fit" in entry["reason"]


def test_suggested_next_day_skips_bank_holidays():
    p = simple_profile(bank_holidays=["2026-11-02"])
    t = tasks("A,Big,300,admin,,3,todo,,,")
    plan = plan_day(p, t, date(2026, 10, 30))
    assert plan.not_today[0]["suggested_day"] == "2026-11-03"


def test_overdue_and_due_today_unplaced_tasks_get_a_note():
    p = simple_profile(fixed_meetings=[{"title": "All morning", "weekday": "mon", "start": "09:00", "end": "13:00"}])
    t = tasks("A,Late,60,admin,2026-10-20,3,todo,,,\nB,Today,60,admin,2026-10-26,3,todo,,,\nC,Later,60,admin,2026-11-20,3,todo,,,")
    plan = plan_day(p, t, MON)
    notes = {n["id"]: n["note"] for n in plan.not_today}
    assert "Already overdue" in notes["A"]
    assert "Due today but not placed" in notes["B"]
    assert notes["C"] == ""


def test_gap_too_small_message_names_the_largest_gap():
    p = simple_profile(fixed_meetings=[{"title": "M", "weekday": "mon", "start": "09:30", "end": "13:00"}])
    plan = plan_day(p, tasks("A,Needs 50,50,admin,,3,todo,,,"), MON)
    # The only gap is 30 minutes (09:00 to 09:30). A 50 minute task is under twice the minimum, so it is never split.
    assert "largest free gap left is 30 minutes" in plan.not_today[0]["reason"]


def test_fixed_commitments_over_capacity_raise_an_alert():
    # Hours 09:00 to 13:00 give W = 240. A 210 minute meeting plus a 60 minute duty is 270.
    p = simple_profile(
        buffer_percent=30,
        fixed_meetings=[{"title": "Workshop", "weekday": "mon", "start": "09:00", "end": "12:30"}],
        recurring_duties=[{"title": "Big check", "cadence": "daily", "minutes": 60}],
    )
    plan = plan_day(p, tasks("A,Task,30,admin,,3,todo,,,"), MON)
    alert = [w for w in plan.warnings if w["level"] == "alert" and "OVERLOADED" in w["message"]]
    assert alert and "Over by 30 min" in alert[0]["message"] and "270 min" in alert[0]["message"]
    assert plan.unplaced_duties == ["Big check"]
    assert plan.task_blocks() == []


def test_no_room_for_tasks_warning_when_commitments_use_up_the_non_buffer_time():
    # W = 240, buffer 30% = 72 rounded to 70. A 180 minute meeting leaves 60, under the buffer.
    p = simple_profile(buffer_percent=30,
                       fixed_meetings=[{"title": "Long", "weekday": "mon", "start": "09:00", "end": "12:00"}])
    plan = plan_day(p, tasks("A,Task,30,admin,,3,todo,,,"), MON)
    assert any("No room for tasks" in w["message"] for w in plan.warnings)
    assert not any("OVERLOADED" in w["message"] for w in plan.warnings)
    assert plan.task_blocks() == [] and plan.not_today[0]["id"] == "A"
    assert plan.capacity["buffer_minutes"] == 60  # all that is free is kept as buffer


def test_no_warning_on_a_normal_day():
    plan = plan_day(profile(), tasks("A,Task,60,admin,,3,todo,,,"), MON)
    assert plan.warnings == []


def test_deep_window_squeezed_by_meetings_warns_when_deep_tasks_wait():
    p = profile(deep_work_window={"start": "09:00", "end": "11:00"},
                fixed_meetings=[{"title": "M", "weekday": "mon", "start": "09:00", "end": "10:45"}])
    plan = plan_day(p, tasks("D,Deep,60,deep,,3,todo,,,"), MON)
    assert any("deep-work window" in w["message"] and "15 minutes" in w["message"] for w in plan.warnings)


def test_duty_preferred_start_rules():
    p = profile(
        fixed_meetings=[{"title": "M", "weekday": "mon", "start": "09:00", "end": "09:30"}],
        recurring_duties=[
            {"id": "a", "title": "At preferred", "cadence": "daily", "minutes": 15, "preferred_start": "10:00"},
            {"id": "b", "title": "Taken slot", "cadence": "daily", "minutes": 15, "preferred_start": "09:10"},
            {"id": "c", "title": "At day end", "cadence": "daily", "minutes": 10, "preferred_start": "18:00"},
            {"id": "d", "title": "No preference", "cadence": "daily", "minutes": 15},
        ],
    )
    plan = plan_day(p, [], MON)
    by_title = {b.title: (b.start, b.end) for b in plan.blocks if b.kind == "duty"}
    assert by_title["At preferred"] == (600, 615)
    assert by_title["Taken slot"] == (570, 585)  # 09:10 is inside the meeting, so the first free time after it
    assert by_title["At day end"] == (16 * 60 + 50, 17 * 60)  # nothing at or after 18:00: the latest start that fits
    assert by_title["No preference"] == (585, 600)  # first free gap
