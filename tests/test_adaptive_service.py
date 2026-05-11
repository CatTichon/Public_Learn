from datetime import UTC, datetime

from app.domain.adaptive_rules import (
    LastResult,
    MasterySnapshot,
    calculate_mastery,
    calculate_next_difficulty,
    should_repeat_topic,
)


def test_mastery_level_recalculation():
    assert calculate_mastery(0, 0) == 0.0
    assert calculate_mastery(3, 4) == 0.75


def test_difficulty_increases_after_fast_correct_answers():
    snapshot = MasterySnapshot(0.8, 2, 5, 4, 1, 15)
    assert calculate_next_difficulty(snapshot, LastResult(True, 10, 2)) == 3


def test_difficulty_decreases_after_errors():
    snapshot = MasterySnapshot(0.25, 3, 4, 1, 3, 30)
    assert calculate_next_difficulty(snapshot, LastResult(False, 25, 3)) == 2


def test_should_repeat_topic_for_empty_profile():
    snapshot = MasterySnapshot(0, 1, 0, 0, 0, 0, datetime.now(UTC))
    assert should_repeat_topic(snapshot)
