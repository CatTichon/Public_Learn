from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest

from app.services.answer_check_service import AnswerCheckService
from tests.support import (
    REPORTS_DIR,
    append_csv_row,
    benchmark_async,
    benchmark_sync,
    summarize_latencies,
)

pytestmark = pytest.mark.performance

REPORT_PATH = REPORTS_DIR / "performance" / "answer_check_latency.csv"
ITERATIONS = 1000


def write_result(test_name: str, check_type: str, stats: dict, **extra) -> None:
    append_csv_row(
        REPORT_PATH,
        {
            "test_name": test_name,
            "check_type": check_type,
            **stats,
            **extra,
        },
    )


def test_numeric_answer_check_latency():
    service = AnswerCheckService()
    task = SimpleNamespace(
        task_type="numeric_answer", correct_answer="42", test_cases=None
    )
    latencies = benchmark_sync(lambda: service.check_answer(task, "42.0"), ITERATIONS)
    stats = summarize_latencies(latencies)
    write_result("test_numeric_answer_check_latency", "numeric_answer", stats)
    assert stats["requests"] == ITERATIONS


def test_text_answer_check_latency():
    service = AnswerCheckService()
    task = SimpleNamespace(
        task_type="text_answer", correct_answer="Париж", test_cases=None
    )
    latencies = benchmark_sync(lambda: service.check_answer(task, "париж"), ITERATIONS)
    stats = summarize_latencies(latencies)
    write_result("test_text_answer_check_latency", "text_answer", stats)
    assert stats["requests"] == ITERATIONS


def test_single_choice_check_latency():
    service = AnswerCheckService()
    task = SimpleNamespace(
        task_type="single_choice",
        correct_answer="24",
        options=["18", "20", "24", "28"],
        test_cases=None,
    )
    latencies = benchmark_sync(lambda: service.check_answer(task, "24"), ITERATIONS)
    stats = summarize_latencies(latencies)
    write_result("test_single_choice_check_latency", "single_choice", stats)
    assert stats["requests"] == ITERATIONS


def test_code_answer_check_latency():
    service = AnswerCheckService()
    task = SimpleNamespace(
        task_type="code_answer",
        correct_answer="add",
        test_cases=[{"input": [2, 3], "expected": 5}],
    )
    answer = "def add(a, b):\n    return a + b"
    latencies = benchmark_sync(lambda: service.check_answer(task, answer), ITERATIONS)
    stats = summarize_latencies(latencies)
    write_result("test_code_answer_check_latency", "code_answer", stats)
    assert stats["requests"] == ITERATIONS


async def test_external_api_check_or_generation_latency_mocked(monkeypatch):
    async def fake_post(self, url, json=None, headers=None):
        del self, url, json, headers
        return httpx.Response(
            200,
            json={"result": "ok", "is_correct": True},
            request=httpx.Request("POST", "https://example.invalid/check"),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    async def external_operation():
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://example.invalid/check",
                json={"answer": "42"},
            )
            response.raise_for_status()
            return response

    latencies, errors = await benchmark_async(external_operation, ITERATIONS)
    stats = summarize_latencies(latencies, errors)
    write_result(
        "test_external_api_check_or_generation_latency_mocked",
        "external_api_mocked",
        stats,
    )
    assert stats["error_rate"] == 0.0


async def test_compare_local_check_vs_external_api_latency(monkeypatch):
    service = AnswerCheckService()
    task = SimpleNamespace(
        task_type="numeric_answer", correct_answer="42", test_cases=None
    )
    local_stats = summarize_latencies(
        benchmark_sync(lambda: service.check_answer(task, "42"), ITERATIONS)
    )

    async def fake_post(self, url, json=None, headers=None):
        del self, url, json, headers
        return httpx.Response(
            200,
            json={"is_correct": True},
            request=httpx.Request("POST", "https://example.invalid/check"),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    async def external_operation():
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://example.invalid/check",
                json={"answer": "42"},
            )
            response.raise_for_status()
            return response

    external_latencies, errors = await benchmark_async(external_operation, ITERATIONS)
    external_stats = summarize_latencies(external_latencies, errors)
    append_csv_row(
        REPORT_PATH,
        {
            "test_name": "test_compare_local_check_vs_external_api_latency",
            "check_type": "comparison",
            "local_mean_ms": local_stats["mean_ms"],
            "external_mean_ms": external_stats["mean_ms"],
            "delta_ms": external_stats["mean_ms"] - local_stats["mean_ms"],
            "local_p95_ms": local_stats["p95_ms"],
            "external_p95_ms": external_stats["p95_ms"],
        },
    )
    assert local_stats["mean_ms"] <= external_stats["mean_ms"]
