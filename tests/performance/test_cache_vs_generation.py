from __future__ import annotations

import pytest

from app.models.topic import Topic
from app.services.content_generation_service import ContentGenerationService
from tests.support import (
    REPORTS_DIR,
    append_csv_row,
    benchmark_async,
    summarize_latencies,
)

pytestmark = pytest.mark.performance

REPORT_PATH = REPORTS_DIR / "performance" / "cache_vs_generation.csv"
ITERATIONS = 80


async def benchmark_generation_once(session_factory, topic_id, redis_cache):
    async def operation():
        async with session_factory() as session:
            service = ContentGenerationService(session, redis_cache)
            task = await service.get_or_generate_task(topic_id, 5)
            await session.rollback()
            return task

    return await benchmark_async(operation, ITERATIONS)


async def benchmark_existing_task(session_factory, topic_id, redis_cache, difficulty):
    async def operation():
        async with session_factory() as session:
            service = ContentGenerationService(session, redis_cache)
            return await service.get_or_generate_task(topic_id, difficulty)

    return await benchmark_async(operation, ITERATIONS)


async def test_cached_task_is_faster_than_template_generation(
    session_factory, seeded_data, redis_cache, settings_override
):
    settings_override(content_generation_mode="template")
    async with session_factory() as session:
        service = ContentGenerationService(session, redis_cache)
        await service.get_or_generate_task(seeded_data.topic_id, 4)
        await session.commit()

    cached_latencies, cached_errors = await benchmark_existing_task(
        session_factory, seeded_data.topic_id, redis_cache, 4
    )
    generation_latencies, generation_errors = await benchmark_generation_once(
        session_factory, seeded_data.topic_id, redis_cache
    )
    cached_stats = summarize_latencies(cached_latencies, cached_errors)
    generation_stats = summarize_latencies(generation_latencies, generation_errors)

    append_csv_row(
        REPORT_PATH,
        {
            "test_name": "test_cached_task_is_faster_than_template_generation",
            "cached_mean_ms": cached_stats["mean_ms"],
            "template_generation_mean_ms": generation_stats["mean_ms"],
            "redis_get_calls": redis_cache.get_calls,
            "redis_setex_calls": redis_cache.setex_calls,
            "observation": (
                "redis_write_only_no_reads"
                if redis_cache.get_calls == 0
                else "redis_reads_detected"
            ),
        },
    )
    assert cached_stats["mean_ms"] <= generation_stats["mean_ms"]
    assert redis_cache.get_calls == 0


async def test_database_task_is_faster_than_template_generation(
    session_factory, seeded_data, redis_cache, settings_override
):
    settings_override(content_generation_mode="template")
    database_latencies, database_errors = await benchmark_existing_task(
        session_factory, seeded_data.topic_id, redis_cache, 1
    )
    generation_latencies, generation_errors = await benchmark_generation_once(
        session_factory, seeded_data.topic_id, redis_cache
    )
    database_stats = summarize_latencies(database_latencies, database_errors)
    generation_stats = summarize_latencies(generation_latencies, generation_errors)

    append_csv_row(
        REPORT_PATH,
        {
            "test_name": "test_database_task_is_faster_than_template_generation",
            "database_mean_ms": database_stats["mean_ms"],
            "template_generation_mean_ms": generation_stats["mean_ms"],
            "database_p95_ms": database_stats["p95_ms"],
            "template_generation_p95_ms": generation_stats["p95_ms"],
        },
    )
    assert database_stats["mean_ms"] <= generation_stats["mean_ms"]


async def test_cache_hit_rate_under_repeated_requests(
    session_factory, seeded_data, redis_cache, settings_override
):
    settings_override(content_generation_mode="template")
    async with session_factory() as session:
        service = ContentGenerationService(session, redis_cache)
        await service.get_or_generate_task(seeded_data.topic_id, 3)
        await session.commit()

    redis_cache.get_calls = 0
    await benchmark_existing_task(session_factory, seeded_data.topic_id, redis_cache, 3)
    hit_rate = redis_cache.get_calls / ITERATIONS if ITERATIONS else 0.0
    append_csv_row(
        REPORT_PATH,
        {
            "test_name": "test_cache_hit_rate_under_repeated_requests",
            "hit_rate": hit_rate,
            "redis_get_calls": redis_cache.get_calls,
            "redis_setex_calls": redis_cache.setex_calls,
            "note": "Current implementation writes generated tasks to Redis but does not read them back.",
        },
    )
    assert hit_rate == 0.0


async def test_cache_miss_triggers_generation(
    session_factory, seeded_data, redis_cache, settings_override, monkeypatch
):
    settings_override(content_generation_mode="template")
    calls = {"generate_task": 0}
    original_generate_task = ContentGenerationService.generate_task

    async def tracked_generate_task(
        self, topic: Topic, difficulty: int, task_type=None
    ):
        calls["generate_task"] += 1
        return await original_generate_task(self, topic, difficulty, task_type)

    monkeypatch.setattr(
        ContentGenerationService, "generate_task", tracked_generate_task
    )

    async with session_factory() as session:
        service = ContentGenerationService(session, redis_cache)
        task = await service.get_or_generate_task(seeded_data.topic_id, 5)
        await session.commit()

    append_csv_row(
        REPORT_PATH,
        {
            "test_name": "test_cache_miss_triggers_generation",
            "generated_task_id": task.id,
            "generate_task_calls": calls["generate_task"],
            "redis_setex_calls": redis_cache.setex_calls,
        },
    )
    assert calls["generate_task"] == 1
    assert redis_cache.setex_calls >= 1
