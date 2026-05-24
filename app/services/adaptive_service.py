from datetime import UTC, datetime

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.adaptive_rules import (
    LastResult,
    MasterySnapshot,
    calculate_mastery,
    calculate_next_difficulty,
    should_repeat_topic,
)
from app.repositories.mastery import MasteryRepository
from app.services.content_generation_service import ContentGenerationService


class AdaptiveService:
    def __init__(self, session: AsyncSession, redis: Redis | None = None):
        self.session = session
        self.mastery_repo = MasteryRepository(session)
        self.content = ContentGenerationService(session, redis)

    async def get_or_create_mastery_profile(self, user_id: int, topic_id: int):
        return await self.mastery_repo.get_or_create(user_id, topic_id)

    def calculate_next_difficulty(
        self, mastery_profile, last_result: LastResult | None = None
    ) -> int:
        return calculate_next_difficulty(self._snapshot(mastery_profile), last_result)

    async def update_mastery_after_answer(
        self,
        user_id: int,
        topic_id: int,
        is_correct: bool,
        answer_time_seconds: float,
        difficulty: int,
    ):
        m = await self.get_or_create_mastery_profile(user_id, topic_id)
        before = m.attempts_count
        m.attempts_count += 1
        if is_correct:
            m.correct_count += 1
        else:
            m.error_count += 1
        m.average_answer_time = (
            answer_time_seconds
            if before == 0
            else ((m.average_answer_time * before) + answer_time_seconds)
            / m.attempts_count
        )
        m.mastery_level = calculate_mastery(m.correct_count, m.attempts_count)
        m.current_difficulty = self.calculate_next_difficulty(
            m, LastResult(is_correct, answer_time_seconds, difficulty)
        )
        m.last_answer_at = datetime.now(UTC)
        await self.session.flush()
        return m

    def should_repeat_topic(self, mastery_profile) -> bool:
        return should_repeat_topic(self._snapshot(mastery_profile))

    async def select_next_task(self, user_id: int, topic_id: int):
        m = await self.get_or_create_mastery_profile(user_id, topic_id)
        difficulty = m.current_difficulty or 1
        return await self.content.get_or_generate_task(topic_id, difficulty)

    def _snapshot(self, m) -> MasterySnapshot:
        return MasterySnapshot(
            m.mastery_level,
            m.current_difficulty,
            m.attempts_count,
            m.correct_count,
            m.error_count,
            m.average_answer_time,
            m.last_answer_at,
        )
