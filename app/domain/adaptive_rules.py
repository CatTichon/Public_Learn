from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(slots=True)
class MasterySnapshot:
    mastery_level: float
    current_difficulty: int
    attempts_count: int
    correct_count: int
    error_count: int
    average_answer_time: float
    last_answer_at: datetime | None = None


@dataclass(slots=True)
class LastResult:
    is_correct: bool
    answer_time_seconds: float
    difficulty: int


def clamp_difficulty(value: int) -> int:
    return max(1, min(5, value))


def calculate_mastery(correct_count: int, attempts_count: int) -> float:
    return 0.0 if attempts_count <= 0 else round(correct_count / attempts_count, 4)


def calculate_next_difficulty(
    snapshot: MasterySnapshot, last_result: LastResult | None
) -> int:
    difficulty = snapshot.current_difficulty or 1
    if last_result is None:
        return clamp_difficulty(
            difficulty + 1 if snapshot.mastery_level >= 0.8 else difficulty
        )
    fast = last_result.answer_time_seconds <= 20
    slow = last_result.answer_time_seconds >= 60
    high = snapshot.mastery_level >= 0.75
    many_errors = (
        snapshot.attempts_count >= 3
        and snapshot.error_count / snapshot.attempts_count >= 0.45
    )
    if last_result.is_correct and fast and high:
        difficulty += 1
    elif last_result.is_correct and slow:
        difficulty += 0
    elif not last_result.is_correct and (many_errors or snapshot.mastery_level < 0.4):
        difficulty -= 1
    return clamp_difficulty(difficulty)


def should_repeat_topic(snapshot: MasterySnapshot, now: datetime | None = None) -> bool:
    now = now or datetime.now(UTC)
    if snapshot.attempts_count == 0:
        return True
    if (
        snapshot.attempts_count >= 3
        and snapshot.error_count / snapshot.attempts_count >= 0.4
    ):
        return True
    if snapshot.last_answer_at and (now - snapshot.last_answer_at).days >= 7:
        return True
    return False
