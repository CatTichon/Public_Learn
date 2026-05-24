from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.mastery import MasteryRepository
from app.repositories.topics import TopicRepository
from app.repositories.users import UserRepository
from app.schemas.user import UserCreate


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)
        self.topics = TopicRepository(session)
        self.mastery = MasteryRepository(session)

    async def get_or_create_from_telegram(
        self, telegram_id: int, username: str | None, first_name: str | None
    ):
        user = await self.users.get_by_telegram_id(telegram_id)
        if user:
            user.username = username
            user.first_name = first_name
            await self.session.flush()
            return user, False
        return (
            await self.users.create(
                UserCreate(
                    telegram_id=telegram_id, username=username, first_name=first_name
                )
            ),
            True,
        )

    async def select_topic(self, user_id: int, topic_id: int):
        user = await self.users.get(user_id)
        topic = await self.topics.get(topic_id)
        if user is None or topic is None:
            raise ValueError("User or topic not found")
        user.selected_topic_id = topic_id
        await self.mastery.get_or_create(user_id, topic_id)
        await self.session.flush()
        return topic
