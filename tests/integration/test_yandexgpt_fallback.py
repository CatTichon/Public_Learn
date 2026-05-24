from __future__ import annotations

import json

import httpx
import pytest

from app.models.topic import Topic
from app.services.content_generation_service import ContentGenerationService

pytestmark = pytest.mark.integration


class MockHTTPResponse:
    def __init__(self, payload=None, *, status_code: int = 200, json_error=None):
        self.payload = payload
        self.status_code = status_code
        self.json_error = json_error
        self.request = httpx.Request("POST", "https://example.invalid/yandexgpt")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "http error",
                request=self.request,
                response=httpx.Response(self.status_code, request=self.request),
            )

    def json(self):
        if self.json_error is not None:
            raise self.json_error
        return self.payload


def response_with_task(task_payload: dict) -> MockHTTPResponse:
    return MockHTTPResponse(
        {
            "result": {
                "alternatives": [
                    {"message": {"text": json.dumps(task_payload, ensure_ascii=False)}}
                ]
            }
        }
    )


async def generate_with_failure(
    session_factory,
    seeded_data,
    settings_override,
    monkeypatch,
    payload_factory,
    *,
    requested_task_type: str,
):
    settings_override(content_generation_mode="yandexgpt")
    payload = payload_factory()

    async def fake_post(self, url, headers=None, json=None):
        del self, url, headers, json
        if isinstance(payload, Exception):
            raise payload
        return payload

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    async with session_factory() as session:
        topic = await session.get(Topic, seeded_data.topic_id)
        service = ContentGenerationService(session)
        task = await service.generate_task(topic, 3, task_type=requested_task_type)
    return task


async def test_yandexgpt_timeout_falls_back_to_template(
    session_factory, seeded_data, settings_override, monkeypatch
):
    task = await generate_with_failure(
        session_factory,
        seeded_data,
        settings_override,
        monkeypatch,
        lambda: httpx.ReadTimeout("timeout"),
        requested_task_type="numeric_answer",
    )
    assert task.source == "generated"
    assert task.task_type == "numeric_answer"


async def test_yandexgpt_http_error_falls_back_to_template(
    session_factory, seeded_data, settings_override, monkeypatch
):
    task = await generate_with_failure(
        session_factory,
        seeded_data,
        settings_override,
        monkeypatch,
        lambda: MockHTTPResponse(status_code=503),
        requested_task_type="numeric_answer",
    )
    assert task.source == "generated"
    assert task.task_type == "numeric_answer"


async def test_yandexgpt_invalid_json_falls_back_to_template(
    session_factory, seeded_data, settings_override, monkeypatch
):
    task = await generate_with_failure(
        session_factory,
        seeded_data,
        settings_override,
        monkeypatch,
        lambda: MockHTTPResponse(json_error=json.JSONDecodeError("bad json", "{}", 0)),
        requested_task_type="numeric_answer",
    )
    assert task.source == "generated"
    assert task.correct_answer


async def test_yandexgpt_invalid_task_type_falls_back_to_template(
    session_factory, seeded_data, settings_override, monkeypatch
):
    task = await generate_with_failure(
        session_factory,
        seeded_data,
        settings_override,
        monkeypatch,
        lambda: response_with_task(
            {
                "task_type": "essay",
                "difficulty": 3,
                "question_text": "Неверная структура.",
                "correct_answer": "42",
                "options": None,
                "starter_code": None,
                "test_cases": None,
                "explanation": "Объяснение.",
            }
        ),
        requested_task_type="numeric_answer",
    )
    assert task.source == "generated"
    assert task.task_type == "numeric_answer"


async def test_yandexgpt_single_choice_without_correct_option_falls_back_to_template(
    session_factory, seeded_data, settings_override, monkeypatch
):
    task = await generate_with_failure(
        session_factory,
        seeded_data,
        settings_override,
        monkeypatch,
        lambda: response_with_task(
            {
                "task_type": "single_choice",
                "difficulty": 3,
                "question_text": "Выберите правильный ответ.",
                "correct_answer": "42",
                "options": ["1", "2", "3", "4"],
                "starter_code": None,
                "test_cases": None,
                "explanation": "Объяснение.",
            }
        ),
        requested_task_type="single_choice",
    )
    assert task.source == "generated"
    assert task.task_type == "single_choice"
    assert task.correct_answer in task.options


async def test_yandexgpt_code_answer_without_tests_falls_back_to_template(
    session_factory, seeded_data, settings_override, monkeypatch
):
    task = await generate_with_failure(
        session_factory,
        seeded_data,
        settings_override,
        monkeypatch,
        lambda: response_with_task(
            {
                "task_type": "code_answer",
                "difficulty": 3,
                "question_text": "Напишите функцию.",
                "correct_answer": "solve",
                "options": None,
                "starter_code": "def solve(x):\n    pass",
                "test_cases": None,
                "explanation": "Объяснение.",
            }
        ),
        requested_task_type="code_answer",
    )
    assert task.source == "generated"
    assert task.task_type == "code_answer"
    assert task.test_cases
