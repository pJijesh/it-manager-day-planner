"""The score formula and the tie-break, with values worked out by hand."""

from datetime import date

from day_planner.scoring import natural_key, score_task, sort_key
from helpers import tasks

ON = date(2026, 10, 26)


def one(row):
    return tasks(row)[0]


def test_importance_due_in_four_days_and_age():
    # importance 5 -> 50; due in 4 days -> 40 - 20 = 20; created 30 days ago -> 30 // 7 = 4
    s = score_task(one("A,x,30,admin,2026-10-30,5,todo,,,2026-09-26"), ON)
    assert (s.importance_points, s.urgency_points, s.age_points, s.total) == (50, 20, 4, 74)


def test_overdue_by_three_days():
    # importance 4 -> 40; overdue 3 -> 40 + 6 = 46; created 22 days ago -> 3
    s = score_task(one("A,x,30,admin,2026-10-23,4,todo,,,2026-10-04"), ON)
    assert (s.urgency_points, s.age_points, s.total) == (46, 3, 89)
    assert "overdue by 3 days" in s.explain()


def test_overdue_bonus_is_capped_at_twenty():
    s = score_task(one("A,x,30,admin,2026-09-01,3,todo,,,"), ON)
    assert s.urgency_points == 60


def test_due_today_tomorrow_a_week_and_beyond():
    def urgency(due):
        return score_task(one(f"A,x,30,admin,{due},3,todo,,,"), ON).urgency_points

    assert urgency("2026-10-26") == 40
    assert urgency("2026-10-27") == 35
    assert urgency("2026-11-02") == 5  # 7 days away
    assert urgency("2026-11-03") == 0  # 8 days away
    assert urgency("2027-01-01") == 0


def test_no_due_date_and_no_created_date():
    s = score_task(one("A,x,30,admin,,3,todo,,,"), ON)
    assert (s.urgency_points, s.age_points, s.total) == (0, 0, 30)
    assert "no due date" in s.explain()


def test_age_is_capped_at_ten_points_and_counts_whole_weeks():
    assert score_task(one("A,x,30,admin,,1,todo,,,2025-01-01"), ON).age_points == 10
    assert score_task(one("A,x,30,admin,,1,todo,,,2026-10-20"), ON).age_points == 0  # 6 days
    assert score_task(one("A,x,30,admin,,1,todo,,,2026-10-19"), ON).age_points == 1  # 7 days


def order(rows):
    items = tasks(rows)
    scored = [(t, score_task(t, ON)) for t in items]
    scored.sort(key=lambda p: sort_key(*p))
    return [t.id for t, _ in scored]


def test_higher_score_first():
    assert order("A,x,30,admin,,2,todo,,,\nB,x,30,admin,,5,todo,,,") == ["B", "A"]


def test_tie_break_earlier_due_date_first():
    # Both score 50: importance 5 with no due date, importance 1 due today (10 + 40).
    assert order("A,x,30,admin,,5,todo,,,\nB,x,30,admin,2026-10-26,1,todo,,,") == ["B", "A"]


def test_tie_break_higher_importance_next():
    # Same due date and same score 40: importance 4 (40) with no age, importance 3 (30) with 10 age points.
    rows = "A,x,30,admin,,3,todo,,,2025-01-01\nB,x,30,admin,,4,todo,,,"
    assert order(rows) == ["B", "A"]


def test_tie_break_shorter_estimate_then_id():
    assert order("A,x,60,admin,,3,todo,,,\nB,x,30,admin,,3,todo,,,") == ["B", "A"]
    assert order("T-10,x,30,admin,,3,todo,,,\nT-2,x,30,admin,,3,todo,,,") == ["T-2", "T-10"]


def test_natural_key():
    assert sorted(["T-10", "T-2", "T-1"], key=natural_key) == ["T-1", "T-2", "T-10"]
    assert natural_key("a-3") == natural_key("A-3")
