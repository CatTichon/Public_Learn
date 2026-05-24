from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.quest import Quest, UserQuest


class QuestRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_active(self):
        return list(
            (
                await self.session.execute(
                    select(Quest).where(Quest.is_active.is_(True)).order_by(Quest.id)
                )
            )
            .scalars()
            .all()
        )

    async def list_for_user(self, user_id: int):
        return list(
            (
                await self.session.execute(
                    select(UserQuest)
                    .options(selectinload(UserQuest.quest))
                    .where(UserQuest.user_id == user_id)
                    .order_by(UserQuest.quest_id)
                )
            )
            .scalars()
            .all()
        )

    async def get_user_quest(self, user_id: int, quest_id: int):
        return (
            await self.session.execute(
                select(UserQuest).where(
                    UserQuest.user_id == user_id, UserQuest.quest_id == quest_id
                )
            )
        ).scalar_one_or_none()

    async def get_or_create_user_quest(self, user_id: int, quest: Quest):
        uq = await self.get_user_quest(user_id, quest.id)
        if uq:
            return uq
        uq = UserQuest(user_id=user_id, quest_id=quest.id, progress=0)
        uq.quest = quest
        self.session.add(uq)
        await self.session.flush()
        return uq
