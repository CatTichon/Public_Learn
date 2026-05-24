from fastapi import APIRouter, Depends, HTTPException, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_cache, get_db_session
from app.repositories.users import UserRepository
from app.schemas.answer import AnswerRequest, AnswerResult
from app.schemas.task import PublicTask
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/next", response_model=PublicTask)
async def next_task(
    user_id: int = Query(...),
    topic_id: int = Query(...),
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_cache),
):
    task = await TaskService(session, redis).next_task(user_id, topic_id)
    await session.commit()
    return PublicTask(
        id=task.id,
        topic_id=task.topic_id,
        task_type=task.task_type,
        difficulty=task.difficulty,
        question_text=task.question_text,
        options=task.options,
        starter_code=task.starter_code,
    )


@router.post("/answer", response_model=AnswerResult)
async def answer_task(
    payload: AnswerRequest,
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_cache),
):
    if await UserRepository(session).get(payload.user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    result = await TaskService(session, redis).answer_task(
        payload.user_id, payload.task_id, payload.answer, payload.answer_time_seconds
    )
    await session.commit()
    task = result["task"]
    return AnswerResult(
        is_correct=result["is_correct"],
        correct_answer=task.correct_answer,
        explanation=task.explanation,
        xp_gained=result["xp_gained"],
        new_level=result["new_level"],
        mastery_level=result["mastery"].mastery_level,
        feedback=result["feedback"],
    )
