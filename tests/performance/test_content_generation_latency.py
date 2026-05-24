from __future__ import annotations

import json

import httpx
import pytest

from app.models.topic import Topic
from app.services.content_generation_service import ContentGenerationService
from tests.support import (
    REPORTS_DIR,
    append_csv_row,
    benchmark_async,
    benchmark_sync,
    summarize_latencies,
)

pytestmark = pytest.mark.performance

REPORT_PATH = REPORTS_DIR / "performance" / "content_generation_latency.csv"
ASYNC_ITERATIONS = 100
SYNC_ITERATIONS = 1000


class MockHTTPResponse:
    def __init__(self, payload=None, *, status_code: int = 200, json_error=None):
        self.payload = payload
        self.status_code = status_code
        self.json_error = json_error
        self.request = httpx.Request("POST", "https://example.invalid/yandexgpt")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "HTTP error",
                request=self.request,
                response=httpx.Response(self.status_code, request=self.request),
            )

    def json(self):
        if self.json_error is not None:
            raise self.json_error
        return self.payload


def yandex_payload(task_payload: dict) -> dict:
    return {
        "result": {
            "alternatives": [
                {"message": {"text": json.dumps(task_payload, ensure_ascii=False)}}
            ]
        }
    }


def write_stats(test_name: str, mode: str, stats: dict, **extra) -> None:
    append_csv_row(
        REPORT_PATH,
        {
            "test_name": test_name,
            "mode": mode,
            **stats,
            **extra,
        },
    )


async def test_get_task_from_database_latency(
    session_factory, seeded_data, settings_override
):
    settings_override(content_generation_mode="template")
    async with session_factory() as session:
        service = ContentGenerationService(session)
        latencies, errors = await benchmark_async(
            lambda: service.get_or_generate_task(seeded_data.topic_id, 1),
            ASYNC_ITERATIONS,
        )
    stats = summarize_latencies(latencies, errors)
    write_stats("test_get_task_from_database_latency", "database", stats)
    assert stats["error_rate"] == 0.0


async def test_template_generation_latency(
    session_factory, seeded_data, settings_override
):
    settings_override(content_generation_mode="template")
    async with session_factory() as session:
        topic = await session.get(Topic, seeded_data.topic_id)
        service = ContentGenerationService(session)
        latencies = benchmark_sync(
            lambda: service.generate_template_task(topic, 4),
            SYNC_ITERATIONS,
        )
    stats = summarize_latencies(latencies)
    write_stats("test_template_generation_latency", "template", stats)
    assert stats["requests"] == SYNC_ITERATIONS


async def test_yandexgpt_generation_latency_mocked(
    session_factory, seeded_data, settings_override, monkeypatch
):
    settings_override(content_generation_mode="yandexgpt")

    async def fake_post(self, url, headers=None, json=None):
        del self, url, headers, json
        return MockHTTPResponse(
            yandex_payload(
                {
                    "task_type": "numeric_answer",
                    "difficulty": 3,
                    "question_text": "Найдите 25% от 80.",
                    "correct_answer": "20",
                    "options": None,
                    "starter_code": None,
                    "test_cases": None,
                    "explanation": "25% от 80 равно 20.",
                }
            )
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    async with session_factory() as session:
        topic = await session.get(Topic, seeded_data.topic_id)
        service = ContentGenerationService(session)
        latencies, errors = await benchmark_async(
            lambda: service.generate_task(topic, 3),
            ASYNC_ITERATIONS,
        )
    stats = summarize_latencies(latencies, errors)
    write_stats("test_yandexgpt_generation_latency_mocked", "yandexgpt_mocked", stats)
    assert stats["error_rate"] == 0.0


async def test_yandexgpt_fallback_latency(
    session_factory, seeded_data, settings_override, monkeypatch
):
    settings_override(content_generation_mode="yandexgpt")
    scenarios = {
        "timeout": lambda: httpx.ReadTimeout("timeout"),
        "http_error": lambda: MockHTTPResponse(status_code=503),
        "invalid_json": lambda: MockHTTPResponse(
            json_error=json.JSONDecodeError("bad json", "{}", 0)
        ),
        "invalid_structure": lambda: MockHTTPResponse(
            yandex_payload(
                {
                    "task_type": "single_choice",
                    "difficulty": 2,
                    "question_text": "Выберите ответ.",
                    "correct_answer": "42",
                    "options": ["1", "2", "3", "4"],
                    "starter_code": None,
                    "test_cases": None,
                    "explanation": "Объяснение задания.",
                }
            )
        ),
    }

    async with session_factory() as session:
        topic = await session.get(Topic, seeded_data.topic_id)
        service = ContentGenerationService(session)
        for scenario_name, factory in scenarios.items():
            payload = factory()

            async def fake_post(self, url, headers=None, json=None, payload=payload):
                del self, url, headers, json
                if isinstance(payload, Exception):
                    raise payload
                return payload

            monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

            async def operation():
                task = await service.generate_task(topic, 3)
                assert task.source == "generated"
                return task

            latencies, errors = await benchmark_async(operation, 40)
            stats = summarize_latencies(latencies, errors)
            write_stats(
                "test_yandexgpt_fallback_latency",
                "fallback",
                stats,
                scenario=scenario_name,
            )
            assert stats["error_rate"] == 0.0


async def test_compare_template_vs_yandexgpt_latency(
    session_factory, seeded_data, settings_override, monkeypatch
):
    async with session_factory() as session:
        topic = await session.get(Topic, seeded_data.topic_id)
        service = ContentGenerationService(session)

        settings_override(content_generation_mode="template")
        template_latencies = benchmark_sync(
            lambda: service.generate_template_task(topic, 2),
            SYNC_ITERATIONS,
        )
        template_stats = summarize_latencies(template_latencies)

        settings_override(content_generation_mode="yandexgpt")

        async def fake_post(self, url, headers=None, json=None):
            del self, url, headers, json
            return MockHTTPResponse(
                yandex_payload(
                    {
                        "task_type": "numeric_answer",
                        "difficulty": 2,
                        "question_text": "Сколько будет 6 + 7?",
                        "correct_answer": "13",
                        "options": None,
                        "starter_code": None,
                        "test_cases": None,
                        "explanation": "6 + 7 = 13.",
                    }
                )
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
        yandex_latencies, errors = await benchmark_async(
            lambda: service.generate_task(topic, 2),
            ASYNC_ITERATIONS,
        )
        yandex_stats = summarize_latencies(yandex_latencies, errors)

    append_csv_row(
        REPORT_PATH,
        {
            "test_name": "test_compare_template_vs_yandexgpt_latency",
            "mode": "comparison",
            "template_mean_ms": template_stats["mean_ms"],
            "yandexgpt_mean_ms": yandex_stats["mean_ms"],
            "delta_ms": yandex_stats["mean_ms"] - template_stats["mean_ms"],
            "template_p95_ms": template_stats["p95_ms"],
            "yandexgpt_p95_ms": yandex_stats["p95_ms"],
        },
    )
    assert yandex_stats["mean_ms"] >= template_stats["mean_ms"]
