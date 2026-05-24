from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.logs import TaskLog, TechnicalLog


class TaskLogRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, **kwargs):
        log = TaskLog(**kwargs)
        self.session.add(log)
        await self.session.flush()
        return log

    async def stats_for_user(self, user_id: int) -> dict:
        total = (
            await self.session.scalar(
                select(func.count(TaskLog.id)).where(TaskLog.user_id == user_id)
            )
            or 0
        )
        correct = (
            await self.session.scalar(
                select(func.count(TaskLog.id)).where(
                    TaskLog.user_id == user_id, TaskLog.is_correct.is_(True)
                )
            )
            or 0
        )
        avg = (
            await self.session.scalar(
                select(func.coalesce(func.avg(TaskLog.answer_time_seconds), 0)).where(
                    TaskLog.user_id == user_id
                )
            )
            or 0
        )
        return {"total": int(total), "correct": int(correct), "avg_time": float(avg)}

    async def count(self) -> int:
        return await self.session.scalar(select(func.count(TaskLog.id))) or 0

    async def average_accuracy(self) -> float:
        total = await self.count()
        if not total:
            return 0.0
        correct = (
            await self.session.scalar(
                select(func.count(TaskLog.id)).where(TaskLog.is_correct.is_(True))
            )
            or 0
        )
        return float(correct) / total


class TechnicalLogRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        event_type: str,
        message: str,
        latency_ms: float | None = None,
        metadata: dict | None = None,
    ):
        log = TechnicalLog(
            event_type=event_type,
            message=message,
            latency_ms=latency_ms,
            metadata_=metadata,
        )
        self.session.add(log)
        await self.session.flush()
        return log

    async def average_latency(self) -> float:
        return float(
            await self.session.scalar(
                select(func.coalesce(func.avg(TechnicalLog.latency_ms), 0))
            )
            or 0.0
        )
