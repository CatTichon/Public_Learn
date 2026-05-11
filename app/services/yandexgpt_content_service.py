import json
import logging
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError, field_validator

from app.core.config import Settings
from app.models.topic import Topic
from app.schemas.task import TaskCreate

logger = logging.getLogger(__name__)


class YandexGPTGenerationError(RuntimeError):
    """Raised when YandexGPT cannot produce a valid task."""


class LLMTaskPayload(BaseModel):
    task_type: str
    difficulty: int = Field(ge=1, le=5)
    question_text: str = Field(min_length=5)
    correct_answer: str = Field(min_length=1)
    options: list[str] | None = None
    starter_code: str | None = None
    test_cases: list[dict[str, Any]] | None = None
    explanation: str = Field(min_length=5)

    @field_validator("task_type")
    @classmethod
    def validate_task_type(cls, value: str) -> str:
        allowed = {"single_choice", "text_answer", "numeric_answer", "code_answer"}
        if value not in allowed:
            raise ValueError(f"task_type must be one of {sorted(allowed)}")
        return value

    @field_validator("options")
    @classmethod
    def validate_options(cls, value: list[str] | None, info) -> list[str] | None:
        if info.data.get("task_type") != "single_choice":
            return value
        if not value or len(value) != 4:
            raise ValueError("single_choice task must contain exactly 4 options")
        if info.data.get("correct_answer") not in value:
            raise ValueError("correct_answer must be present in options")
        return value

    @field_validator("test_cases")
    @classmethod
    def validate_test_cases(
        cls, value: list[dict[str, Any]] | None, info
    ) -> list[dict[str, Any]] | None:
        if info.data.get("task_type") != "code_answer":
            return value
        if not value:
            raise ValueError("code_answer task must contain test_cases")
        for case in value:
            has_call_format = "call" in case and "expected" in case
            has_input_format = "input" in case and "expected" in case
            if not (has_call_format or has_input_format):
                raise ValueError(
                    "each code test case must contain call/expected or input/expected"
                )
        return value


class YandexGPTContentService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def is_configured(self) -> bool:
        return bool(
            self.settings.yandexgpt_folder_id
            and (self.settings.yandexgpt_api_key or self.settings.yandexgpt_iam_token)
        )

    async def generate_task(
        self,
        topic: Topic,
        difficulty: int,
        task_type: str | None = None,
        examples: list[Any] | None = None,
    ) -> TaskCreate:
        if not self.is_configured():
            logger.warning(
                "YandexGPT generation skipped: credentials are not configured"
            )
            raise YandexGPTGenerationError("YandexGPT credentials are not configured")

        payload = self._build_request_payload(
            topic, difficulty, task_type, examples or []
        )
        headers = self._build_headers()

        try:
            logger.info(
                "Requesting YandexGPT task: topic=%s difficulty=%s task_type=%s",
                topic.title,
                difficulty,
                task_type,
            )
            async with httpx.AsyncClient(
                timeout=self.settings.yandexgpt_timeout_seconds
            ) as client:
                response = await client.post(
                    self.settings.yandexgpt_base_url,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise YandexGPTGenerationError("YandexGPT HTTP request failed") from exc

        try:
            text = response.json()["result"]["alternatives"][0]["message"]["text"]
            task_payload = self.parse_task_payload(text)
        except (
            KeyError,
            IndexError,
            TypeError,
            json.JSONDecodeError,
            ValidationError,
        ) as exc:
            raise YandexGPTGenerationError(
                "YandexGPT returned invalid task payload"
            ) from exc

        return TaskCreate(
            topic_id=topic.id,
            task_type=task_payload.task_type,
            difficulty=difficulty,
            question_text=task_payload.question_text,
            correct_answer=task_payload.correct_answer,
            options=task_payload.options,
            starter_code=task_payload.starter_code,
            test_cases=task_payload.test_cases,
            explanation=task_payload.explanation,
            source="yandexgpt",
        )

    def parse_task_payload(self, raw_text: str) -> LLMTaskPayload:
        data = json.loads(self._extract_json(raw_text))
        return LLMTaskPayload.model_validate(data)

    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.settings.yandexgpt_iam_token:
            headers["Authorization"] = f"Bearer {self.settings.yandexgpt_iam_token}"
        else:
            headers["Authorization"] = f"Api-Key {self.settings.yandexgpt_api_key}"
        return headers

    def _build_request_payload(
        self,
        topic: Topic,
        difficulty: int,
        task_type: str | None,
        examples: list[Any] | None = None,
    ) -> dict[str, Any]:
        explicit_uri = (self.settings.yandexgpt_model_uri or "").strip()
        model_uri = explicit_uri or (
            f"gpt://{self.settings.yandexgpt_folder_id}/{self.settings.yandexgpt_model}"
        )
        requested_type = task_type or "numeric_answer, single_choice или code_answer"
        topic_context = (topic.description or "").strip()
        if len(topic_context) > 1200:
            topic_context = topic_context[:1200] + "..."
        examples_context = self._format_examples(examples or [])
        return {
            "modelUri": model_uri,
            "completionOptions": {
                "stream": False,
                "temperature": 0.4,
                "maxTokens": 900,
            },
            "messages": [
                {
                    "role": "system",
                    "text": (
                        "Ты генератор учебных заданий для Telegram-бота. "
                        "Верни только валидный JSON без markdown. "
                        "Задание должно быть школьного уровня, корректным и проверяемым."
                    ),
                },
                {
                    "role": "user",
                    "text": (
                        f"Сгенерируй одно задание по теме '{topic.title}' "
                        f"со сложностью {difficulty} из 5. "
                        f"Контекст темы и теория: {topic_context or 'нет дополнительного контекста'}. "
                        f"Примеры заданий в нужном стиле: {examples_context}. "
                        f"Тип задания: {requested_type}. "
                        "JSON должен иметь поля: task_type, difficulty, question_text, "
                        "correct_answer, options, starter_code, test_cases, explanation. "
                        "task_type: single_choice, text_answer, numeric_answer или code_answer. "
                        "Для single_choice options должен содержать ровно 4 строки, "
                        "и correct_answer обязан быть среди options. "
                        "Для code_answer ученик должен написать одну Python-функцию; "
                        "starter_code должен содержать шаблон функции, а test_cases - список "
                        'объектов вида {"input": [args], "expected": value}. '
                        "Можно добавить function_name в каждый тест. "
                        "Не генерируй задания, требующие import, input, print, файлов, сети или бесконечных циклов. "
                        "correct_answer должен быть короткой строкой без лишних пояснений."
                    ),
                },
            ],
        }

    def _extract_json(self, raw_text: str) -> str:
        """Strip optional markdown fence without corrupting JSON (e.g. backticks in strings)."""
        text = raw_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            if lines and lines[0].lstrip().startswith("```"):
                lines = lines[1:]
            while lines and lines[-1].strip() == "```":
                lines.pop()
            text = "\n".join(lines).strip()
            if text.lower().startswith("json") and not text.lower().startswith("json{"):
                rest = text[4:].lstrip()
                if rest.startswith("{"):
                    text = rest
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise json.JSONDecodeError("JSON object not found", raw_text, 0)
        return text[start : end + 1]

    def _format_examples(self, examples: list[Any]) -> str:
        if not examples:
            return "нет примеров"
        items = []
        for index, task in enumerate(examples, start=1):
            items.append(
                {
                    "example": index,
                    "task_type": getattr(task, "task_type", None),
                    "difficulty": getattr(task, "difficulty", None),
                    "question_text": getattr(task, "question_text", None),
                    "correct_answer": getattr(task, "correct_answer", None),
                    "options": getattr(task, "options", None),
                    "starter_code": getattr(task, "starter_code", None),
                    "test_cases": getattr(task, "test_cases", None),
                    "explanation": getattr(task, "explanation", None),
                }
            )
        return json.dumps(items, ensure_ascii=False)
