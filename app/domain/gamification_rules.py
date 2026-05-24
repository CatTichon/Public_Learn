from datetime import UTC, datetime, timedelta


def calculate_level(xp: int) -> int:
    return xp // 100 + 1


def calculate_answer_xp(is_correct: bool, difficulty: int) -> int:
    return 2 + (10 if is_correct else 3) + max(1, min(5, difficulty)) * 2


def update_streak_values(
    current_streak: int,
    max_streak: int,
    last_activity_at: datetime | None,
    now: datetime | None = None,
) -> tuple[int, int, bool]:
    now = now or datetime.now(UTC)
    today = now.date()
    if last_activity_at is None:
        new = 1
        changed = True
    else:
        last = last_activity_at.date()
        if last == today:
            return current_streak, max_streak, False
        new = current_streak + 1 if last == today - timedelta(days=1) else 1
        changed = True
    return new, max(max_streak, new), changed
