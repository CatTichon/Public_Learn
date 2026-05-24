from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.logs import TechnicalLog
from app.repositories.logs import TechnicalLogRepository

pytestmark = pytest.mark.integration


async def test_response_contains_process_time_header(api_client):
    response = await api_client.get("/health")
    assert response.status_code == 200
    assert "X-Process-Time-ms" in response.headers


async def test_process_time_header_is_float(api_client):
    response = await api_client.get("/health")
    value = response.headers["X-Process-Time-ms"]
    assert float(value) >= 0.0


async def test_technical_log_is_created_for_api_request(api_client, session_factory):
    await api_client.get("/health")
    async with session_factory() as session:
        logs = list((await session.execute(select(TechnicalLog))).scalars().all())
    assert logs
    assert logs[0].event_type == "api_request"


async def test_average_latency_is_calculated_from_technical_logs(
    api_client, session_factory
):
    for _ in range(3):
        await api_client.get("/health")
    async with session_factory() as session:
        rows = list(
            (
                await session.execute(
                    select(TechnicalLog)
                    .where(TechnicalLog.event_type == "api_request")
                    .order_by(TechnicalLog.id)
                )
            )
            .scalars()
            .all()
        )
        average_latency = await TechnicalLogRepository(session).average_latency()
    manual_average = sum(row.latency_ms or 0.0 for row in rows) / len(rows)
    assert rows
    assert average_latency == pytest.approx(manual_average, rel=1e-6)
