from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import select

from app.models.gamification import GamificationLog
from app.models.logs import TaskLog
from app.models.mastery import MasteryProfile
from app.models.quest import UserQuest
from app.models.user import UserProfile
from app.services.task_service import TaskService

pytestmark = pytest.mark.integration


async def collect_state(session_factory, user_id: int, topic_id: int, quest_id: int):
    async with session_factory() as session:
        user = await session.get(UserProfile, user_id)
        mastery = await session.scalar(
            select(MasteryProfile).where(
                MasteryProfile.user_id == user_id,
                MasteryProfile.topic_id == topic_id,
            )
        )
        task_logs = list(
            (
                await session.execute(
                    select(TaskLog)
                    .where(TaskLog.user_id == user_id, TaskLog.topic_id == topic_id)
                    .order_by(TaskLog.id)
                )
            )
            .scalars()
            .all()
        )
        user_quest = await session.scalar(
            select(UserQuest).where(
                UserQuest.user_id == user_id,
                UserQuest.quest_id == quest_id,
            )
        )
        gamification_logs = list(
            (
                await session.execute(
                    select(GamificationLog)
                    .where(GamificationLog.user_id == user_id)
                    .order_by(GamificationLog.id)
                )
            )
            .scalars()
            .all()
        )
        return {
            "user": user,
            "mastery": mastery,
            "task_logs": task_logs,
            "user_quest": user_quest,
            "gamification_logs": gamification_logs,
        }


async def answer_with_service(
    session_factory,
    user_id: int,
    task_id: int,
    answer: str,
    answer_time_seconds: float,
):
    async with session_factory() as session:
        result = await TaskService(session).answer_task(
            user_id, task_id, answer, answer_time_seconds
        )
        await session.commit()
        return result


async def test_answer_creates_task_log_and_updates_mastery(
    session_factory, seeded_data
):
    result = await answer_with_service(
        session_factory, seeded_data.user_id, seeded_data.numeric_task_id, "4", 6.0
    )
    state = await collect_state(
        session_factory, seeded_data.user_id, seeded_data.topic_id, seeded_data.quest_id
    )
    assert result["is_correct"] is True
    assert result["feedback"] == "Ответ верный."
    assert len(state["task_logs"]) == 1
    assert state["mastery"] is not None
    assert state["mastery"].attempts_count == 1
    assert state["mastery"].correct_count == 1


async def test_answer_updates_user_xp_and_level(session_factory, seeded_data):
    async with session_factory() as session:
        user = await session.get(UserProfile, seeded_data.user_id)
        user.xp = 90
        user.level = 1
        await session.commit()

    await answer_with_service(
        session_factory, seeded_data.user_id, seeded_data.numeric_task_id, "4", 5.0
    )
    state = await collect_state(
        session_factory, seeded_data.user_id, seeded_data.topic_id, seeded_data.quest_id
    )
    assert state["user"].xp >= 104
    assert state["user"].level == 2


async def test_answer_updates_quest_progress(session_factory, seeded_data):
    await answer_with_service(
        session_factory, seeded_data.user_id, seeded_data.numeric_task_id, "4", 7.0
    )
    state = await collect_state(
        session_factory, seeded_data.user_id, seeded_data.topic_id, seeded_data.quest_id
    )
    assert state["user_quest"] is not None
    assert state["user_quest"].progress == 1
    assert state["user_quest"].is_completed is False


async def test_answer_writes_gamification_log(session_factory, seeded_data):
    await answer_with_service(
        session_factory, seeded_data.user_id, seeded_data.numeric_task_id, "4", 6.0
    )
    state = await collect_state(
        session_factory, seeded_data.user_id, seeded_data.topic_id, seeded_data.quest_id
    )
    event_types = [log.event_type for log in state["gamification_logs"]]
    assert "xp_added" in event_types
    assert "correct_answer" in event_types


async def test_answer_state_is_consistent_after_commit(session_factory, seeded_data):
    await answer_with_service(
        session_factory, seeded_data.user_id, seeded_data.numeric_task_id, "4", 5.0
    )
    await answer_with_service(
        session_factory, seeded_data.user_id, seeded_data.numeric_task_id, "5", 9.0
    )
    state = await collect_state(
        session_factory, seeded_data.user_id, seeded_data.topic_id, seeded_data.quest_id
    )
    mastery = state["mastery"]
    task_logs = state["task_logs"]
    assert mastery.attempts_count == len(task_logs)
    assert mastery.correct_count >= 0
    assert mastery.error_count >= 0
    assert mastery.average_answer_time >= 0
    assert state["user"].xp >= 0
    assert state["user"].level >= 1
    assert state["user_quest"].progress >= 0


async def test_repeated_answers_do_not_create_invalid_state(
    session_factory, seeded_data
):
    for answer in ("4", "3", "4"):
        await answer_with_service(
            session_factory,
            seeded_data.user_id,
            seeded_data.numeric_task_id,
            answer,
            8.0,
        )
    state = await collect_state(
        session_factory, seeded_data.user_id, seeded_data.topic_id, seeded_data.quest_id
    )
    mastery = state["mastery"]
    assert len(state["task_logs"]) == 3
    assert mastery.attempts_count == 3
    assert mastery.attempts_count == mastery.correct_count + mastery.error_count
    assert mastery.current_difficulty >= 1
    assert mastery.mastery_level >= 0


async def test_parallel_answers_do_not_break_user_progress(
    session_factory, seeded_data
):
    async with session_factory() as session:
        users = [
            UserProfile(telegram_id=5000 + index, username=f"parallel_{index}")
            for index in range(5)
        ]
        session.add_all(users)
        await session.commit()
        user_ids = [user.id for user in users]

    await asyncio.gather(
        *[
            answer_with_service(
                session_factory, user_id, seeded_data.numeric_task_id, "4", 5.0
            )
            for user_id in user_ids
        ]
    )

    for user_id in user_ids:
        state = await collect_state(
            session_factory, user_id, seeded_data.topic_id, seeded_data.quest_id
        )
        assert len(state["task_logs"]) == 1
        assert state["mastery"].attempts_count == 1
        assert state["user"].xp > 0
