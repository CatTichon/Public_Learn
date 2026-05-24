from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.logs import TechnicalLogRepository


class LoggingService:
    def __init__(self, session: AsyncSession):
        self.technical = TechnicalLogRepository(session)

    async def log_technical(
        self,
        event_type: str,
        message: str,
        latency_ms: float | None = None,
        metadata: dict | None = None,
    ):
        return await self.technical.create(event_type, message, latency_ms, metadata)
