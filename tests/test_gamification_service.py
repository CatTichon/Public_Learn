from datetime import UTC, datetime, timedelta

from app.domain.gamification_rules import (
    calculate_answer_xp,
    calculate_level,
    update_streak_values,
)


def test_xp_calculation_includes_difficulty_bonus():
    assert calculate_answer_xp(True, 3) == 18
    assert calculate_answer_xp(False, 2) == 9


def test_level_calculation():
    assert calculate_level(0) == 1
    assert calculate_level(199) == 2
    assert calculate_level(200) == 3


def test_update_streak_yesterday_increments():
    now = datetime(2026, 4, 27, tzinfo=UTC)
    last = now - timedelta(days=1)
    assert update_streak_values(2, 2, last, now) == (3, 3, True)


def test_update_streak_old_activity_resets():
    now = datetime(2026, 4, 27, tzinfo=UTC)
    last = now - timedelta(days=3)
    assert update_streak_values(5, 7, last, now) == (1, 7, True)
