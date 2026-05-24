from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mastery import MasteryProfile


class MasteryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, user_id: int, topic_id: int):
        return (
            await self.session.execute(
                select(MasteryProfile).where(
                    MasteryProfile.user_id == user_id,
                    MasteryProfile.topic_id == topic_id,
                )
            )
        ).scalar_one_or_none()

    async def get_or_create(self, user_id: int, topic_id: int):
        mastery = await self.get(user_id, topic_id)
        if mastery:
            return mastery
        mastery = MasteryProfile(user_id=user_id, topic_id=topic_id)
        self.session.add(mastery)
        await self.session.flush()
        return mastery

    async def list_for_user(self, user_id: int):
        return list(
            (
                await self.session.execute(
                    select(MasteryProfile)
                    .where(MasteryProfile.user_id == user_id)
                    .order_by(MasteryProfile.topic_id)
                )
            )
            .scalars()
            .all()
        )
