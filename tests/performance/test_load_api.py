from __future__ import annotations

import asyncio
from time import perf_counter

import pytest

from app.models.user import UserProfile
from tests.support import REPORTS_DIR, append_csv_row, summarize_latencies

pytestmark = pytest.mark.performance

REPORT_PATH = REPORTS_DIR / "performance" / "load_test.csv"
LOAD_LEVELS = (1, 10, 30, 50)
REQUESTS_PER_USER = 5
FLOW_STEPS = 2


async def create_load_users(session_factory, count: int) -> list[int]:
    async with session_factory() as session:
        users = [
            UserProfile(
                telegram_id=2000 + index,
                username=f"load_user_{index}",
                first_name="Load",
            )
            for index in range(count)
        ]
        session.add_all(users)
        await session.commit()
        return [user.id for user in users]


async def run_concurrent_requests(virtual_users: int, request_per_user):
    latencies: list[float] = []
    errors = 0
    started = perf_counter()

    async def worker(worker_index: int):
        nonlocal errors
        for attempt in range(REQUESTS_PER_USER):
            request_started = perf_counter()
            try:
                response = await request_per_user(worker_index, attempt)
                elapsed = perf_counter() - request_started
                if response.status_code >= 400:
                    errors += 1
                else:
                    latencies.append(elapsed)
            except Exception:
                errors += 1

    await asyncio.gather(*(worker(index) for index in range(virtual_users)))
    total_duration = perf_counter() - started
    stats = summarize_latencies(latencies, errors)
    total_requests = virtual_users * REQUESTS_PER_USER
    stats["throughput_rps"] = total_requests / total_duration if total_duration else 0.0
    return stats


async def run_mixed_flow(virtual_users: int, flow_per_user):
    latencies: list[float] = []
    errors = 0
    started = perf_counter()

    async def worker(worker_index: int):
        nonlocal errors
        for attempt in range(FLOW_STEPS):
            try:
                request_latencies, request_errors = await flow_per_user(
                    worker_index, attempt
                )
                latencies.extend(request_latencies)
                errors += request_errors
            except Exception:
                errors += 2

    await asyncio.gather(*(worker(index) for index in range(virtual_users)))
    total_duration = perf_counter() - started
    stats = summarize_latencies(latencies, errors)
    total_requests = virtual_users * FLOW_STEPS * 2
    stats["throughput_rps"] = total_requests / total_duration if total_duration else 0.0
    return stats


def write_load_row(test_name: str, virtual_users: int, stats: dict) -> None:
    append_csv_row(
        REPORT_PATH,
        {
            "test_name": test_name,
            "virtual_users": virtual_users,
            "mean_ms": stats["mean_ms"],
            "p95_ms": stats["p95_ms"],
            "p99_ms": stats["p99_ms"],
            "median_ms": stats["median_ms"],
            "std_ms": stats["std_ms"],
            "throughput_rps": stats["throughput_rps"],
            "error_rate": stats["error_rate"],
            "requests": stats["requests"],
        },
    )


async def test_concurrent_health_requests(api_client):
    for virtual_users in LOAD_LEVELS:
        stats = await run_concurrent_requests(
            virtual_users,
            lambda worker_index, attempt: api_client.get("/health"),
        )
        write_load_row("test_concurrent_health_requests", virtual_users, stats)
        assert stats["error_rate"] == 0.0


async def test_concurrent_next_task_requests(
    api_client, session_factory, seeded_data, settings_override
):
    settings_override(content_generation_mode="template")
    user_ids = await create_load_users(session_factory, max(LOAD_LEVELS))
    for virtual_users in LOAD_LEVELS:
        stats = await run_concurrent_requests(
            virtual_users,
            lambda worker_index, attempt: api_client.get(
                "/tasks/next",
                params={
                    "user_id": user_ids[worker_index],
                    "topic_id": seeded_data.topic_id,
                },
            ),
        )
        write_load_row("test_concurrent_next_task_requests", virtual_users, stats)
        assert stats["error_rate"] == 0.0


async def test_concurrent_answer_requests(api_client, session_factory, seeded_data):
    user_ids = await create_load_users(session_factory, max(LOAD_LEVELS))
    for virtual_users in LOAD_LEVELS:
        stats = await run_concurrent_requests(
            virtual_users,
            lambda worker_index, attempt: api_client.post(
                "/tasks/answer",
                json={
                    "user_id": user_ids[worker_index],
                    "task_id": seeded_data.numeric_task_id,
                    "answer": "4",
                    "answer_time_seconds": 6.0 + attempt,
                },
            ),
        )
        write_load_row("test_concurrent_answer_requests", virtual_users, stats)
        assert stats["error_rate"] == 0.0


async def test_concurrent_mixed_user_flow(
    api_client, session_factory, seeded_data, settings_override
):
    settings_override(content_generation_mode="template")
    user_ids = await create_load_users(session_factory, max(LOAD_LEVELS))
    answer_map = {
        seeded_data.numeric_task_id: "4",
        seeded_data.harder_task_id: "9",
    }

    async def flow_per_user(worker_index: int, attempt: int):
        latencies: list[float] = []
        errors = 0

        started = perf_counter()
        next_response = await api_client.get(
            "/tasks/next",
            params={
                "user_id": user_ids[worker_index],
                "topic_id": seeded_data.topic_id,
            },
        )
        latencies.append(perf_counter() - started)
        if next_response.status_code >= 400:
            return latencies, 1

        task_id = next_response.json()["id"]
        answer = answer_map.get(task_id, "4")
        started = perf_counter()
        answer_response = await api_client.post(
            "/tasks/answer",
            json={
                "user_id": user_ids[worker_index],
                "task_id": task_id,
                "answer": answer,
                "answer_time_seconds": 5.0 + attempt,
            },
        )
        latencies.append(perf_counter() - started)
        if answer_response.status_code >= 400:
            errors += 1
        return latencies, errors

    for virtual_users in LOAD_LEVELS:
        stats = await run_mixed_flow(virtual_users, flow_per_user)
        write_load_row("test_concurrent_mixed_user_flow", virtual_users, stats)
        assert stats["error_rate"] == 0.0
