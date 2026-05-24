from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gamification import Achievement, GamificationLog, UserAchievement


class GamificationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log_event(self, **kwargs):
        log = GamificationLog(**kwargs)
        self.session.add(log)
        await self.session.flush()
        return log

    async def count_events(self) -> int:
        return await self.session.scalar(select(func.count(GamificationLog.id))) or 0


class AchievementRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_all(self):
        return list(
            (await self.session.execute(select(Achievement).order_by(Achievement.id)))
            .scalars()
            .all()
        )

    async def get_by_code(self, code: str):
        return (
            await self.session.execute(
                select(Achievement).where(Achievement.code == code)
            )
        ).scalar_one_or_none()

    async def user_has(self, user_id: int, achievement_id: int) -> bool:
        return (
            await self.session.execute(
                select(UserAchievement.id).where(
                    UserAchievement.user_id == user_id,
                    UserAchievement.achievement_id == achievement_id,
                )
            )
        ).scalar_one_or_none() is not None

    async def unlock(self, user_id: int, achievement_id: int, unlocked_at):
        item = UserAchievement(
            user_id=user_id, achievement_id=achievement_id, unlocked_at=unlocked_at
        )
        self.session.add(item)
        await self.session.flush()
        return item
