from __future__ import annotations

import pytest

from tests.support import (
    REPORTS_DIR,
    append_csv_row,
    benchmark_async,
    summarize_latencies,
)

pytestmark = pytest.mark.performance

REPORT_PATH = REPORTS_DIR / "performance" / "api_response_time.csv"
ITERATIONS = 120


async def record_api_benchmark(name, method, endpoint, operation):
    latencies, errors = await benchmark_async(
        operation,
        ITERATIONS,
        error_predicate=lambda response: response.status_code >= 400,
    )
    stats = summarize_latencies(latencies, errors)
    append_csv_row(
        REPORT_PATH,
        {
            "test_name": name,
            "method": method,
            "endpoint": endpoint,
            **stats,
        },
    )
    return stats


async def test_health_response_time(api_client):
    stats = await record_api_benchmark(
        "test_health_response_time",
        "GET",
        "/health",
        lambda: api_client.get("/health"),
    )
    assert stats["error_rate"] == 0.0


async def test_next_task_response_time(api_client, seeded_data):
    stats = await record_api_benchmark(
        "test_next_task_response_time",
        "GET",
        "/tasks/next",
        lambda: api_client.get(
            "/tasks/next",
            params={"user_id": seeded_data.user_id, "topic_id": seeded_data.topic_id},
        ),
    )
    assert stats["error_rate"] == 0.0


async def test_answer_task_response_time(api_client, seeded_data):
    stats = await record_api_benchmark(
        "test_answer_task_response_time",
        "POST",
        "/tasks/answer",
        lambda: api_client.post(
            "/tasks/answer",
            json={
                "user_id": seeded_data.user_id,
                "task_id": seeded_data.numeric_task_id,
                "answer": "4",
                "answer_time_seconds": 7.5,
            },
        ),
    )
    assert stats["error_rate"] == 0.0


async def test_user_stats_response_time(api_client, seeded_data):
    await api_client.post(
        "/tasks/answer",
        json={
            "user_id": seeded_data.user_id,
            "task_id": seeded_data.numeric_task_id,
            "answer": "4",
            "answer_time_seconds": 9,
        },
    )
    stats = await record_api_benchmark(
        "test_user_stats_response_time",
        "GET",
        f"/users/{seeded_data.user_id}/stats",
        lambda: api_client.get(f"/users/{seeded_data.user_id}/stats"),
    )
    assert stats["error_rate"] == 0.0


async def test_analytics_summary_response_time(api_client, seeded_data):
    await api_client.get(
        "/tasks/next",
        params={"user_id": seeded_data.user_id, "topic_id": seeded_data.topic_id},
    )
    stats = await record_api_benchmark(
        "test_analytics_summary_response_time",
        "GET",
        "/analytics/summary",
        lambda: api_client.get("/analytics/summary"),
    )
    assert stats["error_rate"] == 0.0


async def test_user_progress_response_time(api_client, seeded_data):
    await api_client.post(
        "/tasks/answer",
        json={
            "user_id": seeded_data.user_id,
            "task_id": seeded_data.numeric_task_id,
            "answer": "4",
            "answer_time_seconds": 8,
        },
    )
    stats = await record_api_benchmark(
        "test_user_progress_response_time",
        "GET",
        f"/analytics/users/{seeded_data.user_id}/progress",
        lambda: api_client.get(f"/analytics/users/{seeded_data.user_id}/progress"),
    )
    assert stats["error_rate"] == 0.0
