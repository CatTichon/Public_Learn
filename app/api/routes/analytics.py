from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.schemas.analytics import AnalyticsSummary, TopicProgress
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/users/{user_id}/progress", response_model=list[TopicProgress])
async def user_progress(user_id: int, session: AsyncSession = Depends(get_db_session)):
    return await AnalyticsService(session).progress(user_id)


@router.get("/summary", response_model=AnalyticsSummary)
async def summary(session: AsyncSession = Depends(get_db_session)):
    return await AnalyticsService(session).summary()
