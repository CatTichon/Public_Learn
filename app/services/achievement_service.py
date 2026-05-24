from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.gamification import AchievementRepository


class AchievementService:
    def __init__(self, session: AsyncSession):
        self.achievements = AchievementRepository(session)

    async def list_all(self):
        return await self.achievements.list_all()
