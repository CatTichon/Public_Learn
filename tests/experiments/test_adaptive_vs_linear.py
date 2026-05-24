from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.domain.adaptive_rules import (
    LastResult,
    MasterySnapshot,
    calculate_mastery,
    calculate_next_difficulty,
    clamp_difficulty,
)
from tests.support import REPORTS_DIR, write_csv_rows

pytestmark = pytest.mark.experiment

REPORT_PATH = REPORTS_DIR / "experiments" / "adaptive_vs_linear.csv"
ATTEMPTS = 8


@dataclass(slots=True)
class SimulationState:
    current_difficulty: int = 1
    attempts_count: int = 0
    correct_count: int = 0
    error_count: int = 0
    average_answer_time: float = 0.0


def user_response(user_type: str, attempt: int, difficulty: int) -> tuple[bool, float]:
    if user_type == "strong":
        is_correct = difficulty <= 4
        return is_correct, 8.0 if is_correct else 35.0
    if user_type == "weak":
        is_correct = (difficulty == 1 and attempt <= 2) or (
            difficulty == 1 and attempt % 4 == 0
        )
        return is_correct, 18.0 if is_correct else 72.0
    if user_type == "average":
        is_correct = difficulty <= 2 if attempt % 2 else difficulty <= 3
        return is_correct, 16.0 if is_correct else 48.0
    if user_type == "unstable":
        if attempt <= 3:
            return False, 68.0
        is_correct = difficulty <= 3
        return is_correct, 12.0 if is_correct else 42.0
    raise ValueError(f"Unknown user_type: {user_type}")


def linear_next_difficulty(attempt: int) -> int:
    return clamp_difficulty(1 + attempt // 2)


def adaptation_correct(
    mode: str,
    is_correct: bool,
    answer_time: float,
    current_difficulty: int,
    next_difficulty: int,
) -> bool:
    if mode == "linear":
        return next_difficulty >= current_difficulty or next_difficulty == 1
    if is_correct and answer_time <= 20:
        return next_difficulty >= current_difficulty
    if not is_correct:
        return next_difficulty <= current_difficulty
    return next_difficulty == current_difficulty


def simulate(mode: str, user_type: str, attempts: int = ATTEMPTS) -> list[dict]:
    rows: list[dict] = []
    state = SimulationState()
    for attempt in range(1, attempts + 1):
        current = state.current_difficulty
        is_correct, answer_time = user_response(user_type, attempt, current)
        state.attempts_count += 1
        if is_correct:
            state.correct_count += 1
        else:
            state.error_count += 1
        previous_attempts = state.attempts_count - 1
        state.average_answer_time = (
            answer_time
            if previous_attempts == 0
            else ((state.average_answer_time * previous_attempts) + answer_time)
            / state.attempts_count
        )
        mastery_level = calculate_mastery(state.correct_count, state.attempts_count)
        if mode == "adaptive":
            next_difficulty = calculate_next_difficulty(
                MasterySnapshot(
                    mastery_level=mastery_level,
                    current_difficulty=current,
                    attempts_count=state.attempts_count,
                    correct_count=state.correct_count,
                    error_count=state.error_count,
                    average_answer_time=state.average_answer_time,
                    last_answer_at=None,
                ),
                LastResult(is_correct, answer_time, current),
            )
        else:
            next_difficulty = linear_next_difficulty(attempt)
        rows.append(
            {
                "mode": mode,
                "user_type": user_type,
                "attempt": attempt,
                "is_correct": is_correct,
                "answer_time": answer_time,
                "current_difficulty": current,
                "next_difficulty": next_difficulty,
                "mastery_level": mastery_level,
                "adaptation_correct": adaptation_correct(
                    mode, is_correct, answer_time, current, next_difficulty
                ),
            }
        )
        state.current_difficulty = next_difficulty
    write_csv_rows(REPORT_PATH, rows)
    return rows


def test_adaptive_reaches_mastery_with_fewer_too_hard_tasks():
    adaptive_rows = simulate("adaptive", "weak")
    linear_rows = simulate("linear", "weak")
    adaptive_too_hard = sum(
        1
        for row in adaptive_rows
        if not row["is_correct"] and row["current_difficulty"] > 1
    )
    linear_too_hard = sum(
        1
        for row in linear_rows
        if not row["is_correct"] and row["current_difficulty"] > 1
    )
    assert adaptive_too_hard <= linear_too_hard


def test_adaptive_reduces_difficulty_after_repeated_errors():
    adaptive_rows = simulate("adaptive", "weak")
    assert any(
        row["attempt"] >= 3 and row["next_difficulty"] < row["current_difficulty"]
        for row in adaptive_rows
    )


def test_adaptive_increases_difficulty_after_successful_fast_answers():
    adaptive_rows = simulate("adaptive", "strong")
    assert any(
        row["is_correct"]
        and row["answer_time"] <= 20
        and row["next_difficulty"] > row["current_difficulty"]
        for row in adaptive_rows
    )


def test_linear_mode_does_not_react_to_errors():
    linear_rows = simulate("linear", "weak")
    assert all(
        row["next_difficulty"] >= row["current_difficulty"]
        for row in linear_rows
        if not row["is_correct"]
    )


def test_compare_adaptive_vs_linear_learning_curve():
    adaptive_rows = simulate("adaptive", "unstable")
    linear_rows = simulate("linear", "unstable")
    adaptive_final_mastery = adaptive_rows[-1]["mastery_level"]
    linear_final_mastery = linear_rows[-1]["mastery_level"]
    adaptive_early_difficulty = (
        sum(row["current_difficulty"] for row in adaptive_rows[:4]) / 4
    )
    linear_early_difficulty = (
        sum(row["current_difficulty"] for row in linear_rows[:4]) / 4
    )
    assert adaptive_early_difficulty <= linear_early_difficulty
    assert adaptive_final_mastery >= linear_final_mastery
