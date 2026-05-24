from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TaskCreate(BaseModel):
    topic_id: int
    task_type: str
    difficulty: int = Field(ge=1, le=5)
    question_text: str
    correct_answer: str
    options: list[str] | None = None
    starter_code: str | None = None
    test_cases: list[dict] | None = None
    explanation: str
    source: str = "generated"


class TaskRead(BaseModel):
    id: int
    topic_id: int
    task_type: str
    difficulty: int
    question_text: str
    correct_answer: str
    options: list[str] | None
    starter_code: str | None
    test_cases: list[dict] | None
    explanation: str
    source: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PublicTask(BaseModel):
    id: int
    topic_id: int
    task_type: str
    difficulty: int
    question_text: str
    options: list[str] | None = None
    starter_code: str | None = None
