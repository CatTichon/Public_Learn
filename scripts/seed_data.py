import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import select

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import AsyncSessionLocal
from app.models.gamification import Achievement
from app.models.quest import Quest
from app.models.task import Task
from app.models.topic import Topic

ROOT_DIR = Path(__file__).resolve().parents[1]
EGE_DATASET_PATH = ROOT_DIR / "data" / "ege_profile_math_2026.json"


async def first_or_none(session, stmt):
    """Return the first matching row; seed data must tolerate old duplicate rows."""
    return (await session.execute(stmt.limit(1))).scalars().first()


TOPICS = [
    ("Арифметика", "Сложение, вычитание, умножение и деление."),
    ("Проценты", "Нахождение процентов и изменение величин."),
    ("Уравнения", "Линейные уравнения базового уровня."),
    ("Геометрия", "Площадь и периметр простых фигур."),
    ("Программирование", "Практические задания на написание простых функций Python."),
]
TASKS = {
    "Арифметика": [
        ("numeric_answer", 1, "Вычислите: 7 + 5", "12", None, "7 + 5 = 12."),
        ("numeric_answer", 1, "Вычислите: 14 - 6", "8", None, "14 - 6 = 8."),
        (
            "single_choice",
            2,
            "Вычислите: 6 * 4",
            "24",
            ["20", "22", "24", "26"],
            "6 * 4 = 24.",
        ),
        (
            "numeric_answer",
            3,
            "Вычислите: 45 / 5",
            "9",
            None,
            "45 делим на 5, получаем 9.",
        ),
        ("numeric_answer", 4, "Вычислите: 18 * 7", "126", None, "18 * 7 = 126."),
    ],
    "Проценты": [
        ("numeric_answer", 1, "Найдите 10% от 80", "8", None, "80 * 0.10 = 8."),
        ("numeric_answer", 2, "Найдите 15% от 200", "30", None, "200 * 0.15 = 30."),
        (
            "single_choice",
            2,
            "Найдите 25% от 120",
            "30",
            ["20", "25", "30", "35"],
            "120 * 0.25 = 30.",
        ),
        (
            "numeric_answer",
            3,
            "Число увеличили на 20% и получили 60. Найдите исходное число",
            "50",
            None,
            "60 / 1.2 = 50.",
        ),
        ("numeric_answer", 4, "Найдите 12.5% от 320", "40", None, "320 * 0.125 = 40."),
    ],
    "Уравнения": [
        ("numeric_answer", 1, "Решите: x + 4 = 9", "5", None, "x = 9 - 4 = 5."),
        ("numeric_answer", 1, "Решите: x - 3 = 7", "10", None, "x = 7 + 3 = 10."),
        (
            "single_choice",
            2,
            "Решите: 3x = 12",
            "4",
            ["3", "4", "5", "6"],
            "x = 12 / 3 = 4.",
        ),
        ("numeric_answer", 3, "Решите: 2x + 5 = 17", "6", None, "2x = 12, x = 6."),
        ("numeric_answer", 4, "Решите: 5x - 10 = 35", "9", None, "5x = 45, x = 9."),
    ],
    "Геометрия": [
        (
            "numeric_answer",
            1,
            "Площадь квадрата со стороной 5",
            "25",
            None,
            "S = a^2 = 25.",
        ),
        (
            "numeric_answer",
            1,
            "Периметр квадрата со стороной 6",
            "24",
            None,
            "P = 4a = 24.",
        ),
        (
            "single_choice",
            2,
            "Площадь прямоугольника 4 на 7",
            "28",
            ["22", "24", "28", "32"],
            "S = 4 * 7 = 28.",
        ),
        (
            "numeric_answer",
            3,
            "Периметр прямоугольника 8 на 11",
            "38",
            None,
            "P = 2 * (8 + 11) = 38.",
        ),
        (
            "numeric_answer",
            4,
            "Площадь прямоугольника 13 на 9",
            "117",
            None,
            "S = 13 * 9 = 117.",
        ),
    ],
    "Программирование": [
        (
            "code_answer",
            1,
            "Напишите функцию add(a, b), которая возвращает сумму двух чисел.",
            "def add(a, b):\n    return a + b",
            None,
            "Функция должна вернуть результат сложения a и b.",
        ),
        (
            "code_answer",
            1,
            "Напишите функцию is_even(n), которая возвращает True, если число четное.",
            "def is_even(n):\n    return n % 2 == 0",
            None,
            "Число четное, если остаток от деления на 2 равен 0.",
        ),
        (
            "code_answer",
            2,
            "Напишите функцию max_of_two(a, b), которая возвращает большее из двух чисел.",
            "def max_of_two(a, b):\n    return a if a >= b else b",
            None,
            "Сравните два значения и верните большее.",
        ),
        (
            "code_answer",
            2,
            "Напишите функцию count_vowels(text), которая считает русские и английские гласные.",
            "def count_vowels(text):\n    return sum(1 for ch in text.lower() if ch in 'aeiouаеёиоуыэюя')",
            None,
            "Нужно привести строку к нижнему регистру и посчитать символы из набора гласных.",
        ),
        (
            "code_answer",
            3,
            "Напишите функцию factorial(n), которая возвращает факториал неотрицательного числа n.",
            "def factorial(n):\n    result = 1\n    for value in range(2, n + 1):\n        result *= value\n    return result",
            None,
            "Факториал — произведение всех целых чисел от 1 до n.",
        ),
    ],
}

CODE_TASK_DATA = {
    "Напишите функцию add(a, b), которая возвращает сумму двух чисел.": {
        "starter_code": "def add(a, b):\n    pass",
        "test_cases": {
            "function_name": "add",
            "tests": [
                {"input": [2, 3], "expected": 5},
                {"input": [-1, 1], "expected": 0},
                {"input": [10, 15], "expected": 25},
            ],
        },
    },
    "Напишите функцию is_even(n), которая возвращает True, если число четное.": {
        "starter_code": "def is_even(n):\n    pass",
        "test_cases": {
            "function_name": "is_even",
            "tests": [
                {"input": [2], "expected": True},
                {"input": [3], "expected": False},
                {"input": [0], "expected": True},
            ],
        },
    },
    "Напишите функцию max_of_two(a, b), которая возвращает большее из двух чисел.": {
        "starter_code": "def max_of_two(a, b):\n    pass",
        "test_cases": {
            "function_name": "max_of_two",
            "tests": [
                {"input": [2, 7], "expected": 7},
                {"input": [8, 1], "expected": 8},
                {"input": [4, 4], "expected": 4},
            ],
        },
    },
    "Напишите функцию count_vowels(text), которая считает русские и английские гласные.": {
        "starter_code": "def count_vowels(text):\n    pass",
        "test_cases": {
            "function_name": "count_vowels",
            "tests": [
                {"input": ["hello"], "expected": 2},
                {"input": ["Привет"], "expected": 2},
                {"input": ["xyz"], "expected": 0},
            ],
        },
    },
    "Напишите функцию factorial(n), которая возвращает факториал неотрицательного числа n.": {
        "starter_code": "def factorial(n):\n    pass",
        "test_cases": {
            "function_name": "factorial",
            "tests": [
                {"input": [0], "expected": 1},
                {"input": [3], "expected": 6},
                {"input": [5], "expected": 120},
            ],
        },
    },
}
ACHIEVEMENTS = [
    (
        "first_correct_answer",
        "Первый успех",
        "Дать первый правильный ответ",
        "first_correct_answer",
        1,
        20,
    ),
    (
        "ten_tasks_completed",
        "Десяток заданий",
        "Выполнить 10 заданий",
        "tasks_completed",
        10,
        30,
    ),
    (
        "five_correct_answers",
        "Пять верных",
        "Набрать 5 правильных ответов",
        "correct_answers",
        5,
        25,
    ),
    (
        "three_day_streak",
        "Три дня подряд",
        "Поддерживать серию 3 дня",
        "streak_days",
        3,
        40,
    ),
    (
        "topic_master",
        "Мастер темы",
        "Достичь освоения темы 80%",
        "topic_mastery",
        80,
        50,
    ),
]
QUESTS = [
    (
        "daily_3_tasks",
        "Ежедневный рывок",
        "Решить 3 задания за день",
        "daily",
        3,
        20,
        None,
    ),
    (
        "weekly_20_tasks",
        "Недельный марафон",
        "Решить 20 заданий за неделю",
        "weekly",
        20,
        80,
        None,
    ),
    (
        "thematic_5_tasks",
        "Тематическая практика",
        "Решить 5 заданий по выбранной теме",
        "thematic",
        5,
        35,
        None,
    ),
]


async def seed_base_topics_and_tasks(session) -> None:
    topic_map = {}
    for title, desc in TOPICS:
        topic = (
            await session.execute(select(Topic).where(Topic.title == title))
        ).scalar_one_or_none()
        if topic is None:
            topic = Topic(title=title, description=desc)
            session.add(topic)
            await session.flush()
        topic_map[title] = topic
    for title, tasks in TASKS.items():
        for task_type, difficulty, question, answer, options, explanation in tasks:
            if (
                await first_or_none(
                    session, select(Task).where(Task.question_text == question)
                )
                is None
            ):
                session.add(
                    Task(
                        topic_id=topic_map[title].id,
                        task_type=task_type,
                        difficulty=difficulty,
                        question_text=question,
                        correct_answer=answer,
                        options=options,
                        explanation=explanation,
                        source="seed",
                    )
                )


async def seed_ege_profile_math(session) -> None:
    if not EGE_DATASET_PATH.exists():
        return

    dataset = json.loads(EGE_DATASET_PATH.read_text(encoding="utf-8"))
    topic_map = {}
    for item in dataset.get("topics", []):
        title = item["title"]
        description = (
            f"{dataset.get('exam', 'ЕГЭ профильная математика')}\n"
            f"Код темы: {item.get('code')}. "
            f"Номер задания: {item.get('ege_number')}. "
            f"Уровень: {item.get('level')}.\n\n"
            f"{item.get('description', '')}"
        )
        topic = (
            await session.execute(select(Topic).where(Topic.title == title))
        ).scalar_one_or_none()
        if topic is None:
            topic = Topic(title=title, description=description)
            session.add(topic)
            await session.flush()
        else:
            topic.description = description
        topic_map[title] = topic

    for title, tasks in dataset.get("tasks_by_topic", {}).items():
        topic = topic_map.get(title)
        if topic is None:
            continue
        for raw_task in tasks:
            task_data = _normalize_ege_task(raw_task)
            if (
                await first_or_none(
                    session,
                    select(Task).where(
                        Task.question_text == task_data["question_text"]
                    ),
                )
                is not None
            ):
                continue
            task_kwargs = {
                "topic_id": topic.id,
                "task_type": task_data["task_type"],
                "difficulty": task_data["difficulty"],
                "question_text": task_data["question_text"],
                "correct_answer": task_data["correct_answer"],
                "options": task_data.get("options"),
                "explanation": task_data["explanation"],
                "source": task_data.get("source", "author_seed_ege_2026"),
            }
            if hasattr(Task, "starter_code"):
                task_kwargs["starter_code"] = task_data.get("starter_code")
            if hasattr(Task, "test_cases"):
                task_kwargs["test_cases"] = task_data.get("test_cases")
            session.add(Task(**task_kwargs))


def _normalize_ege_task(raw_task: list | dict) -> dict:
    if isinstance(raw_task, dict):
        return {
            "task_type": raw_task["task_type"],
            "difficulty": raw_task["difficulty"],
            "question_text": raw_task["question_text"],
            "correct_answer": raw_task["correct_answer"],
            "options": raw_task.get("options"),
            "starter_code": raw_task.get("starter_code"),
            "test_cases": raw_task.get("test_cases"),
            "explanation": raw_task["explanation"],
            "source": raw_task.get("source", "author_seed_ege_2026"),
        }
    task_type, difficulty, question, answer, options, explanation = raw_task[:6]
    return {
        "task_type": task_type,
        "difficulty": difficulty,
        "question_text": question,
        "correct_answer": answer,
        "options": options,
        "starter_code": None,
        "test_cases": None,
        "explanation": explanation,
        "source": "author_seed_ege_2026",
    }


async def main() -> None:
    async with AsyncSessionLocal() as session:
        await seed_base_topics_and_tasks(session)
        await seed_ege_profile_math(session)
        for code, title, desc, ctype, cval, xp in ACHIEVEMENTS:
            if (
                await first_or_none(
                    session, select(Achievement).where(Achievement.code == code)
                )
                is None
            ):
                session.add(
                    Achievement(
                        code=code,
                        title=title,
                        description=desc,
                        condition_type=ctype,
                        condition_value=cval,
                        xp_reward=xp,
                    )
                )
        for code, title, desc, qtype, target, xp, topic_id in QUESTS:
            if (
                await first_or_none(session, select(Quest).where(Quest.code == code))
                is None
            ):
                session.add(
                    Quest(
                        code=code,
                        title=title,
                        description=desc,
                        quest_type=qtype,
                        target_value=target,
                        xp_reward=xp,
                        topic_id=topic_id,
                        is_active=True,
                    )
                )
        await session.commit()
        print("Seed data loaded")


if __name__ == "__main__":
    asyncio.run(main())
