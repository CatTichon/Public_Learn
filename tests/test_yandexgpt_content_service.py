import json

import pytest
from pydantic import ValidationError

from app.services.yandexgpt_content_service import YandexGPTContentService


def make_service() -> YandexGPTContentService:
    return YandexGPTContentService(settings=object())


def test_parse_task_from_plain_json():
    service = make_service()
    task = service.parse_task_payload(
        '{"task_type":"numeric_answer","difficulty":2,'
        '"question_text":"Найдите 10% от 80.","correct_answer":"8",'
        '"options":null,"explanation":"80 * 0.10 = 8."}'
    )

    assert task.task_type == "numeric_answer"
    assert task.difficulty == 2
    assert task.correct_answer == "8"


def test_parse_task_from_markdown_code_block():
    service = make_service()
    task = service.parse_task_payload(
        """```json
        {
          "task_type": "single_choice",
          "difficulty": 3,
          "question_text": "Сколько будет 6 * 4?",
          "correct_answer": "24",
          "options": ["18", "20", "24", "28"],
          "explanation": "6 * 4 = 24."
        }
        ```""",
    )

    assert task.task_type == "single_choice"
    assert task.difficulty == 3
    assert task.options == ["18", "20", "24", "28"]


def test_single_choice_must_include_correct_answer():
    service = make_service()
    with pytest.raises(ValidationError):
        service.parse_task_payload(
            '{"task_type":"single_choice","difficulty":2,'
            '"question_text":"Выберите ответ.","correct_answer":"24",'
            '"options":["18","20","22","28"],"explanation":"Подробное объяснение."}'
        )


def test_parse_code_answer_payload():
    service = make_service()
    task = service.parse_task_payload("""
        {
          "task_type": "code_answer",
          "difficulty": 2,
          "question_text": "Напишите функцию add(a, b).",
          "correct_answer": "Функция должна вернуть сумму.",
          "options": null,
          "explanation": "Используйте оператор +.",
          "starter_code": "def add(a, b):\\n    pass",
          "test_cases": [
            {"input": [2, 3], "expected": 5}
          ]
        }
        """)

    assert task.task_type == "code_answer"
    assert task.starter_code == "def add(a, b):\n    pass"
    assert task.test_cases == [{"input": [2, 3], "expected": 5}]


def test_extract_json_preserves_backticks_inside_strings():
    class Settings:
        yandexgpt_folder_id = "f"
        yandexgpt_model = "m"

    service = YandexGPTContentService(Settings())
    raw = """```json
{
  "task_type": "text_answer",
  "difficulty": 2,
  "question_text": "Что такое `list` в Python?",
  "correct_answer": "list",
  "options": null,
  "starter_code": null,
  "test_cases": null,
  "explanation": "В Python `list` — изменяемая последовательность."
}
```"""
    extracted = service._extract_json(raw)
    assert "`list`" in extracted
    data = json.loads(extracted)
    assert "list" in data["question_text"]


def test_build_request_payload_uses_explicit_model_uri():
    class Settings:
        yandexgpt_folder_id = "folder123"
        yandexgpt_model = "ignored"
        yandexgpt_model_uri = "gpt://folder123/custom/model"

    class Topic:
        title = "Тема"
        description = ""

    service = YandexGPTContentService(Settings())
    payload = service._build_request_payload(Topic(), difficulty=1, task_type=None)
    assert payload["modelUri"] == "gpt://folder123/custom/model"



def test_request_payload_contains_examples():
    class Settings:
        yandexgpt_folder_id = "folder"
        yandexgpt_model = "yandexgpt-lite"
        yandexgpt_model_uri = ""

    class Topic:
        title = "ЕГЭ профиль №1"
        description = "Площади и подобие."

    class ExampleTask:
        task_type = "numeric_answer"
        difficulty = 2
        question_text = "Сторона квадрата 7. Найдите площадь."
        correct_answer = "49"
        options = None
        starter_code = None
        test_cases = None
        explanation = "7^2 = 49."

    service = YandexGPTContentService(Settings())
    payload = service._build_request_payload(
        Topic(),
        difficulty=2,
        task_type=None,
        examples=[ExampleTask()],
    )

    user_message = payload["messages"][1]["text"]
    assert "Примеры заданий в нужном стиле" in user_message
    assert "Сторона квадрата 7" in user_message
