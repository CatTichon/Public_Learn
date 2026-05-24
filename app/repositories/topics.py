from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.topic import Topic


class TopicRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, topic_id: int):
        return await self.session.get(Topic, topic_id)

    async def get_by_title(self, title: str):
        return (
            await self.session.execute(select(Topic).where(Topic.title == title))
        ).scalar_one_or_none()

    async def list_active(self) -> list[Topic]:
        return list(
            (
                await self.session.execute(
                    select(Topic).where(Topic.is_active.is_(True)).order_by(Topic.id)
                )
            )
            .scalars()
            .all()
        )

    async def create(self, title: str, description: str):
        topic = Topic(title=title, description=description)
        self.session.add(topic)
        await self.session.flush()
        return topic
