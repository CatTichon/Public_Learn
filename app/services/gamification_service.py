from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.gamification_rules import (
    calculate_answer_xp,
    calculate_level,
    update_streak_values,
)
from app.repositories.gamification import AchievementRepository, GamificationRepository
from app.repositories.logs import TaskLogRepository
from app.repositories.mastery import MasteryRepository
from app.repositories.quests import QuestRepository
from app.repositories.users import UserRepository
from app.schemas.gamification import XpResult


class GamificationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)
        self.logs = GamificationRepository(session)
        self.task_logs = TaskLogRepository(session)
        self.achievements = AchievementRepository(session)
        self.quests = QuestRepository(session)
        self.mastery = MasteryRepository(session)

    def calculate_level(self, xp: int) -> int:
        return calculate_level(xp)

    def calculate_answer_xp(self, is_correct: bool, difficulty: int) -> int:
        return calculate_answer_xp(is_correct, difficulty)

    async def add_xp(self, user_id: int, amount: int, reason: str) -> XpResult:
        user = await self.users.get(user_id)
        if user is None:
            raise ValueError("User not found")
        old = user.level
        user.xp += amount
        user.level = self.calculate_level(user.xp)
        await self.log_gamification_event(
            user_id,
            "level_up" if user.level > old else "xp_added",
            amount,
            reason,
            old,
            user.level,
        )
        await self.session.flush()
        return XpResult(
            xp_gained=amount,
            old_level=old,
            new_level=user.level,
            leveled_up=user.level > old,
        )

    async def update_streak(self, user_id: int) -> bool:
        user = await self.users.get(user_id)
        if user is None:
            raise ValueError("User not found")
        now = datetime.now(UTC)
        new, max_streak, changed = update_streak_values(
            user.current_streak, user.max_streak, user.last_activity_at, now
        )
        user.current_streak = new
        user.max_streak = max_streak
        user.last_activity_at = now
        if changed:
            await self.log_gamification_event(
                user_id, "streak_updated", 0, f"Серия обновлена: {new}"
            )
        await self.session.flush()
        return changed

    async def check_achievements(self, user_id: int) -> list:
        unlocked = []
        user = await self.users.get(user_id)
        stats = await self.task_logs.stats_for_user(user_id)
        mastery = await self.mastery.list_for_user(user_id)
        for ach in await self.achievements.list_all():
            if await self.achievements.user_has(user_id, ach.id):
                continue
            if self._achievement_condition_met(ach, user, stats, mastery):
                await self.achievements.unlock(user_id, ach.id, datetime.now(UTC))
                unlocked.append(ach)
                await self.add_xp(user_id, ach.xp_reward, f"Достижение: {ach.title}")
                await self.log_gamification_event(
                    user_id, "achievement_unlocked", ach.xp_reward, ach.code
                )
        return unlocked

    async def update_quests(
        self, user_id: int, event_type: str, topic_id: int | None = None
    ) -> list:
        completed = []
        if event_type != "task_completed":
            return completed
        for quest in await self.quests.list_active():
            if quest.topic_id is not None and quest.topic_id != topic_id:
                continue
            uq = await self.quests.get_or_create_user_quest(user_id, quest)
            if uq.is_completed:
                continue
            uq.progress += 1
            if uq.progress >= quest.target_value:
                await self.complete_quest(user_id, quest.id)
                completed.append(quest)
        await self.session.flush()
        return completed

    async def complete_quest(self, user_id: int, quest_id: int) -> None:
        uq = await self.quests.get_user_quest(user_id, quest_id)
        if uq is None:
            return
        uq.is_completed = True
        uq.completed_at = datetime.now(UTC)
        quest = uq.quest
        await self.add_xp(user_id, quest.xp_reward, f"Квест: {quest.title}")
        await self.log_gamification_event(
            user_id, "quest_completed", quest.xp_reward, quest.code
        )

    async def log_gamification_event(
        self,
        user_id: int,
        event_type: str,
        xp_delta: int,
        reason: str,
        old_level: int | None = None,
        new_level: int | None = None,
    ) -> None:
        user = await self.users.get(user_id)
        await self.logs.log_event(
            user_id=user_id,
            event_type=event_type,
            xp_delta=xp_delta,
            old_level=old_level or (user.level if user else 1),
            new_level=new_level or (user.level if user else 1),
            reason=reason,
        )

    def _achievement_condition_met(
        self, ach, user, stats: dict, mastery_profiles: list
    ) -> bool:
        if ach.condition_type == "first_correct_answer":
            return stats["correct"] >= 1
        if ach.condition_type == "tasks_completed":
            return stats["total"] >= ach.condition_value
        if ach.condition_type == "correct_answers":
            return stats["correct"] >= ach.condition_value
        if ach.condition_type == "streak_days":
            return bool(user and user.current_streak >= ach.condition_value)
        if ach.condition_type == "topic_mastery":
            return any(
                m.mastery_level >= ach.condition_value / 100 for m in mastery_profiles
            )
        return False
