from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.gamification import GamificationLog
from app.models.user import UserProfile

pytestmark = pytest.mark.integration


async def test_full_learning_flow_correct_answer(api_client, seeded_data):
    next_response = await api_client.get(
        "/tasks/next",
        params={"user_id": seeded_data.user_id, "topic_id": seeded_data.topic_id},
    )
    assert next_response.status_code == 200
    task = next_response.json()

    answer_response = await api_client.post(
        "/tasks/answer",
        json={
            "user_id": seeded_data.user_id,
            "task_id": task["id"],
            "answer": "4",
            "answer_time_seconds": 5.0,
        },
    )
    payload = answer_response.json()
    assert answer_response.status_code == 200
    assert payload["is_correct"] is True
    assert payload["xp_gained"] > 0
    assert payload["feedback"] == "Ответ верный."


async def test_full_learning_flow_wrong_answer(api_client, seeded_data):
    answer_response = await api_client.post(
        "/tasks/answer",
        json={
            "user_id": seeded_data.user_id,
            "task_id": seeded_data.numeric_task_id,
            "answer": "999",
            "answer_time_seconds": 11.0,
        },
    )
    payload = answer_response.json()
    assert answer_response.status_code == 200
    assert payload["is_correct"] is False
    assert payload["feedback"] == "2 + 2 = 4."
    assert payload["correct_answer"] == "4"


async def test_full_learning_flow_next_task_uses_updated_difficulty(
    api_client, seeded_data
):
    answer_response = await api_client.post(
        "/tasks/answer",
        json={
            "user_id": seeded_data.user_id,
            "task_id": seeded_data.numeric_task_id,
            "answer": "4",
            "answer_time_seconds": 6.0,
        },
    )
    assert answer_response.status_code == 200

    next_response = await api_client.get(
        "/tasks/next",
        params={"user_id": seeded_data.user_id, "topic_id": seeded_data.topic_id},
    )
    payload = next_response.json()
    assert next_response.status_code == 200
    assert payload["difficulty"] == 2
    assert payload["id"] == seeded_data.harder_task_id


async def test_full_learning_flow_profile_stats_are_updated(api_client, seeded_data):
    await api_client.post(
        "/tasks/answer",
        json={
            "user_id": seeded_data.user_id,
            "task_id": seeded_data.numeric_task_id,
            "answer": "4",
            "answer_time_seconds": 8.0,
        },
    )
    stats_response = await api_client.get(f"/users/{seeded_data.user_id}/stats")
    progress_response = await api_client.get(
        f"/analytics/users/{seeded_data.user_id}/progress"
    )

    stats_payload = stats_response.json()
    progress_payload = progress_response.json()
    assert stats_response.status_code == 200
    assert progress_response.status_code == 200
    assert stats_payload["total_tasks"] == 1
    assert stats_payload["correct_answers"] == 1
    assert stats_payload["accuracy"] == 1.0
    assert progress_payload[0]["current_difficulty"] == 2


async def test_full_learning_flow_gamification_is_updated(
    api_client, session_factory, seeded_data
):
    await api_client.post(
        "/tasks/answer",
        json={
            "user_id": seeded_data.user_id,
            "task_id": seeded_data.numeric_task_id,
            "answer": "4",
            "answer_time_seconds": 7.0,
        },
    )
    async with session_factory() as session:
        user = await session.get(UserProfile, seeded_data.user_id)
        logs = list(
            (
                await session.execute(
                    select(GamificationLog).where(
                        GamificationLog.user_id == seeded_data.user_id
                    )
                )
            )
            .scalars()
            .all()
        )
    assert user.xp > 0
    assert any(log.event_type == "correct_answer" for log in logs)
