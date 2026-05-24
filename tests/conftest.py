from __future__ import annotations

from dataclasses import dataclass

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.api.deps import get_cache, get_db_session
from app.core.database import Base
from app.main import create_app
from app.models.gamification import Achievement
from app.models.quest import Quest
from app.models.task import Task
from app.models.topic import Topic
from app.models.user import UserProfile
from tests.support import FakeRedis, make_test_settings


@dataclass(slots=True)
class SeededData:
    user_id: int
    topic_id: int
    numeric_task_id: int
    harder_task_id: int
    text_task_id: int
    code_task_id: int
    quest_id: int


@pytest.fixture
def settings_override(monkeypatch: pytest.MonkeyPatch):
    def _override(**overrides):
        settings = make_test_settings(**overrides)
        monkeypatch.setattr("app.core.logging.get_settings", lambda: settings)
        monkeypatch.setattr(
            "app.services.content_generation_service.get_settings", lambda: settings
        )
        return settings

    return _override


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    database_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")

    @event.listens_for(engine.sync_engine, "connect")
    def _sqlite_pragmas(dbapi_connection, connection_record):
        del connection_record
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(session_factory):
    async with session_factory() as session:
        yield session


@pytest.fixture
def redis_cache() -> FakeRedis:
    return FakeRedis()


@pytest_asyncio.fixture
async def app_with_overrides(session_factory, redis_cache, settings_override):
    settings_override()
    app = create_app()

    async def override_db_session():
        async with session_factory() as session:
            yield session

    async def override_cache():
        yield redis_cache

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_cache] = override_cache
    app.state.session_factory = session_factory
    yield app
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def api_client(app_with_overrides):
    async with AsyncClient(
        transport=ASGITransport(app=app_with_overrides), base_url="http://test"
    ) as client:
        yield client


@pytest_asyncio.fixture
async def seeded_data(session_factory) -> SeededData:
    async with session_factory() as session:
        topic = Topic(title="Арифметика", description="Базовые арифметические задачи.")
        user = UserProfile(
            telegram_id=101,
            username="student",
            first_name="Student",
            xp=0,
            level=1,
        )
        numeric_task = Task(
            topic=topic,
            task_type="numeric_answer",
            difficulty=1,
            question_text="Сколько будет 2 + 2?",
            correct_answer="4",
            explanation="2 + 2 = 4.",
            source="seed",
        )
        harder_task = Task(
            topic=topic,
            task_type="numeric_answer",
            difficulty=2,
            question_text="Сколько будет 3 * 3?",
            correct_answer="9",
            explanation="3 * 3 = 9.",
            source="seed",
        )
        text_task = Task(
            topic=topic,
            task_type="text_answer",
            difficulty=1,
            question_text="Назовите столицу Франции.",
            correct_answer="Париж",
            explanation="Столица Франции — Париж.",
            source="seed",
        )
        code_task = Task(
            topic=topic,
            task_type="code_answer",
            difficulty=1,
            question_text="Напишите функцию add(a, b), которая возвращает сумму.",
            correct_answer="add",
            starter_code="def add(a, b):\n    pass",
            test_cases=[
                {"input": [2, 3], "expected": 5},
                {"input": [-1, 1], "expected": 0},
            ],
            explanation="Нужно вернуть сумму a + b.",
            source="seed",
        )
        quest = Quest(
            code="daily-arithmetic",
            title="Реши три задачи",
            description="Решите три задания по теме.",
            quest_type="daily",
            target_value=3,
            xp_reward=20,
            topic=topic,
            is_active=True,
        )
        achievement = Achievement(
            code="hundred-correct",
            title="Большая серия",
            description="Сделать много заданий.",
            condition_type="tasks_completed",
            condition_value=100,
            xp_reward=50,
        )
        session.add_all(
            [
                topic,
                user,
                numeric_task,
                harder_task,
                text_task,
                code_task,
                quest,
                achievement,
            ]
        )
        await session.commit()
        return SeededData(
            user_id=user.id,
            topic_id=topic.id,
            numeric_task_id=numeric_task.id,
            harder_task_id=harder_task.id,
            text_task_id=text_task.id,
            code_task_id=code_task.id,
            quest_id=quest.id,
        )
