from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.quests import QuestRepository


class QuestService:
    def __init__(self, session: AsyncSession):
        self.quests = QuestRepository(session)

    async def list_user_quests(self, user_id: int):
        for quest in await self.quests.list_active():
            await self.quests.get_or_create_user_quest(user_id, quest)
        return await self.quests.list_for_user(user_id)
