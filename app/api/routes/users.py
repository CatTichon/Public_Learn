from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.repositories.users import UserRepository
from app.schemas.user import UserRead, UserStats
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: int, session: AsyncSession = Depends(get_db_session)):
    user = await UserRepository(session).get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/{user_id}/stats", response_model=UserStats)
async def get_user_stats(user_id: int, session: AsyncSession = Depends(get_db_session)):
    return await AnalyticsService(session).user_stats(user_id)
