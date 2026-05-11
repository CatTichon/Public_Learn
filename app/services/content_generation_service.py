import json
import logging
import random

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.domain.task_generation_rules import make_options
from app.models.topic import Topic
from app.repositories.tasks import TaskRepository
from app.repositories.topics import TopicRepository
from app.schemas.task import TaskCreate
from app.services.yandexgpt_content_service import YandexGPTContentService

logger = logging.getLogger(__name__)


class ContentGenerationService:
    def __init__(self, session: AsyncSession, redis: Redis | None = None):
        self.session = session
        self.redis = redis
        self.tasks = TaskRepository(session)
        self.topics = TopicRepository(session)

    async def get_or_generate_task(
        self, topic_id: int, difficulty: int, task_type: str | None = None
    ):
        topic = await self.topics.get(topic_id)
        if topic is None:
            raise ValueError("Topic not found")
        settings = get_settings()
        if settings.content_generation_mode.lower() != "yandexgpt":
            task = await self.tasks.find_for_topic(topic_id, difficulty, task_type)
            if task:
                return task
        create = await self.generate_task(topic, difficulty, task_type)
        task = await self.tasks.create(create)
        await self._cache_task(task)
        return task

    async def generate_task(
        self, topic: Topic, difficulty: int, task_type: str | None = None
    ) -> TaskCreate:
        settings = get_settings()
        if settings.content_generation_mode.lower() == "yandexgpt":
            try:
                examples = await self.tasks.list_examples_for_topic(
                    topic_id=topic.id,
                    limit=settings.yandexgpt_few_shot_examples,
                    task_type=task_type,
                )
                return await YandexGPTContentService(settings).generate_task(
                    topic=topic,
                    difficulty=difficulty,
                    task_type=task_type,
                    examples=examples,
                )
            except Exception:
                logger.exception(
                    "YandexGPT task generation failed; using template fallback"
                )
        return self.generate_template_task(topic, difficulty, task_type)

    def generate_template_task(
        self, topic: Topic, difficulty: int, task_type: str | None = None
    ) -> TaskCreate:
        title = topic.title.lower()
        task_type = task_type or random.choice(
            ["numeric_answer", "single_choice", "code_answer"]
        )
        if task_type == "code_answer":
            return self._code_task(topic.id, difficulty)
        if "процент" in title:
            create = self._percent(topic.id, difficulty)
        elif "урав" in title:
            create = self._equation(topic.id, difficulty)
        elif "геометр" in title:
            create = self._geometry(topic.id, difficulty)
        else:
            create = self._arithmetic(topic.id, difficulty)
        if task_type == "single_choice":
            create.task_type = "single_choice"
            create.options = make_options(int(float(create.correct_answer)), difficulty)
        return create

    def build_error_explanation(self, task) -> str:
        return (
            task.explanation
            or f"Правильный ответ: {task.correct_answer}. Повтори правило и попробуй похожее задание."
        )

    def _arithmetic(self, topic_id: int, difficulty: int) -> TaskCreate:
        limit = 10 * difficulty
        a = random.randint(1, limit)
        b = random.randint(1, limit)
        op = random.choice(["+", "-", "*"] if difficulty > 1 else ["+", "-"])
        if op == "+":
            ans = a + b
            expl = f"Складываем {a} и {b}: получаем {ans}."
        elif op == "-":
            a, b = max(a, b), min(a, b)
            ans = a - b
            expl = f"Вычитаем {b} из {a}: получаем {ans}."
        else:
            ans = a * b
            expl = f"Умножаем {a} на {b}: получаем {ans}."
        return TaskCreate(
            topic_id=topic_id,
            task_type="numeric_answer",
            difficulty=difficulty,
            question_text=f"Вычислите: {a} {op} {b}",
            correct_answer=str(ans),
            explanation=expl,
        )

    def _percent(self, topic_id: int, difficulty: int) -> TaskCreate:
        percent = random.choice([5, 10, 15, 20, 25, 30])
        number = random.randint(4, 20) * 10 * difficulty
        ans = number * percent / 100
        text = str(int(ans)) if ans.is_integer() else f"{ans:.2f}"
        return TaskCreate(
            topic_id=topic_id,
            task_type="numeric_answer",
            difficulty=difficulty,
            question_text=f"Найдите {percent}% от {number}.",
            correct_answer=text,
            explanation=f"Чтобы найти {percent}% от {number}, умножаем {number} на {percent/100:.2f}. Получаем {text}.",
        )

    def _equation(self, topic_id: int, difficulty: int) -> TaskCreate:
        x = random.randint(1, 10 * difficulty)
        a = random.randint(1, 5 * difficulty)
        b = random.randint(1, 8 * difficulty)
        if difficulty <= 2:
            q = f"Решите уравнение: x + {a} = {x+a}"
            e = f"Вычитаем {a} из обеих частей: x = {x}."
        else:
            q = f"Решите уравнение: {a}x + {b} = {a*x+b}"
            e = f"Сначала вычитаем {b}, затем делим на {a}: x = {x}."
        return TaskCreate(
            topic_id=topic_id,
            task_type="numeric_answer",
            difficulty=difficulty,
            question_text=q,
            correct_answer=str(x),
            explanation=e,
        )

    def _geometry(self, topic_id: int, difficulty: int) -> TaskCreate:
        a = random.randint(2, 5 * difficulty)
        b = random.randint(2, 5 * difficulty)
        if random.choice([True, False]):
            ans = a * b
            q = f"Найдите площадь прямоугольника со сторонами {a} и {b}."
            e = f"Площадь равна a * b: {a} * {b} = {ans}."
        else:
            ans = 2 * (a + b)
            q = f"Найдите периметр прямоугольника со сторонами {a} и {b}."
            e = f"Периметр равен 2 * (a + b): 2 * ({a} + {b}) = {ans}."
        return TaskCreate(
            topic_id=topic_id,
            task_type="numeric_answer",
            difficulty=difficulty,
            question_text=q,
            correct_answer=str(ans),
            explanation=e,
        )

    def _code_task(self, topic_id: int, difficulty: int) -> TaskCreate:
        examples = [
            {
                "question": "Напишите функцию add(a, b), которая возвращает сумму двух чисел.",
                "starter": "def add(a, b):\n    pass",
                "function": "add",
                "tests": [
                    {"input": [2, 3], "expected": 5},
                    {"input": [-1, 1], "expected": 0},
                    {"input": [10, 15], "expected": 25},
                ],
                "explanation": "Функция должна вернуть a + b.",
            },
            {
                "question": "Напишите функцию is_even(n), которая возвращает True, если число четное.",
                "starter": "def is_even(n):\n    pass",
                "function": "is_even",
                "tests": [
                    {"input": [2], "expected": True},
                    {"input": [3], "expected": False},
                    {"input": [0], "expected": True},
                ],
                "explanation": "Число четное, если остаток от деления на 2 равен 0.",
            },
            {
                "question": "Напишите функцию max_of_two(a, b), которая возвращает большее из двух чисел.",
                "starter": "def max_of_two(a, b):\n    pass",
                "function": "max_of_two",
                "tests": [
                    {"input": [2, 5], "expected": 5},
                    {"input": [7, 1], "expected": 7},
                    {"input": [4, 4], "expected": 4},
                ],
                "explanation": "Нужно сравнить два числа и вернуть большее.",
            },
        ]
        data = examples[min(len(examples) - 1, max(0, difficulty - 1))]
        return TaskCreate(
            topic_id=topic_id,
            task_type="code_answer",
            difficulty=difficulty,
            question_text=data["question"],
            correct_answer=data["function"],
            options=None,
            explanation=data["explanation"],
            source="generated",
            starter_code=data["starter"],
            test_cases=data["tests"],
        )

    async def _cache_task(self, task) -> None:
        if self.redis:
            await self.redis.setex(
                f"task:{task.topic_id}:{task.difficulty}:{task.task_type}",
                3600,
                json.dumps({"id": task.id}),
            )
