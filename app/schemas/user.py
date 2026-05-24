from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str | None = None


class UserRead(BaseModel):
    id: int
    telegram_id: int
    username: str | None
    first_name: str | None
    level: int
    xp: int
    current_streak: int
    max_streak: int
    last_activity_at: datetime | None
    selected_topic_id: int | None
    model_config = ConfigDict(from_attributes=True)


class UserStats(BaseModel):
    total_tasks: int
    correct_answers: int
    accuracy: float
    average_answer_time: float
    current_streak: int
    max_streak: int
