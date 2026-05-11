from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.schemas.task import TaskCreate


class TaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, task_id: int):
        return await self.session.get(Task, task_id)

    async def find_for_topic(
        self, topic_id: int, difficulty: int, task_type: str | None = None
    ):
        stmt = select(Task).where(
            Task.topic_id == topic_id, Task.difficulty == difficulty
        )
        if task_type:
            stmt = stmt.where(Task.task_type == task_type)
        return (
            await self.session.execute(stmt.order_by(Task.id).limit(1))
        ).scalar_one_or_none()

    async def list_examples_for_topic(
        self, topic_id: int, limit: int = 3, task_type: str | None = None
    ) -> list[Task]:
        stmt = select(Task).where(Task.topic_id == topic_id)
        if task_type:
            stmt = stmt.where(Task.task_type == task_type)
        result = await self.session.execute(
            stmt.order_by(Task.difficulty, Task.id).limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, data: TaskCreate):
        task = Task(**data.model_dump())
        self.session.add(task)
        await self.session.flush()
        return task
