from pydantic import BaseModel, Field


class AnswerRequest(BaseModel):
    user_id: int
    task_id: int
    answer: str
    answer_time_seconds: float = Field(default=0.0, ge=0)


class AnswerResult(BaseModel):
    is_correct: bool
    correct_answer: str
    explanation: str
    xp_gained: int
    new_level: int
    mastery_level: float
    feedback: str | None = None
