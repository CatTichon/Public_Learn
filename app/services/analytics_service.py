from sqlalchemy.ext.asyncio import AsyncSession

from app.models.topic import Topic
from app.repositories.gamification import GamificationRepository
from app.repositories.logs import TaskLogRepository, TechnicalLogRepository
from app.repositories.mastery import MasteryRepository
from app.repositories.users import UserRepository
from app.schemas.analytics import AnalyticsSummary, TopicProgress
from app.schemas.user import UserStats


class AnalyticsService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)
        self.task_logs = TaskLogRepository(session)
        self.tech_logs = TechnicalLogRepository(session)
        self.game_logs = GamificationRepository(session)
        self.mastery = MasteryRepository(session)

    async def user_stats(self, user_id: int) -> UserStats:
        stats = await self.task_logs.stats_for_user(user_id)
        user = await self.users.get(user_id)
        total = stats["total"]
        return UserStats(
            total_tasks=total,
            correct_answers=stats["correct"],
            accuracy=stats["correct"] / total if total else 0.0,
            average_answer_time=stats["avg_time"],
            current_streak=user.current_streak if user else 0,
            max_streak=user.max_streak if user else 0,
        )

    async def progress(self, user_id: int) -> list[TopicProgress]:
        items = []
        for m in await self.mastery.list_for_user(user_id):
            topic = await self.session.get(Topic, m.topic_id)
            items.append(
                TopicProgress(
                    topic_id=m.topic_id,
                    topic_title=topic.title if topic else "",
                    mastery_level=m.mastery_level,
                    attempts_count=m.attempts_count,
                    correct_count=m.correct_count,
                    current_difficulty=m.current_difficulty,
                )
            )
        return items

    async def summary(self) -> AnalyticsSummary:
        return AnalyticsSummary(
            users_count=await self.users.count(),
            solved_tasks_count=await self.task_logs.count(),
            average_accuracy=await self.task_logs.average_accuracy(),
            average_latency_ms=await self.tech_logs.average_latency(),
            gamification_events_count=await self.game_logs.count_events(),
        )
