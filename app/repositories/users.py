from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserProfile
from app.schemas.user import UserCreate


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, user_id: int):
        return await self.session.get(UserProfile, user_id)

    async def get_by_telegram_id(self, telegram_id: int):
        return (
            await self.session.execute(
                select(UserProfile).where(UserProfile.telegram_id == telegram_id)
            )
        ).scalar_one_or_none()

    async def create(self, data: UserCreate):
        user = UserProfile(**data.model_dump())
        self.session.add(user)
        await self.session.flush()
        return user

    async def count(self) -> int:
        return await self.session.scalar(select(func.count(UserProfile.id))) or 0
