from pydantic import BaseModel


class TopicProgress(BaseModel):
    topic_id: int
    topic_title: str
    mastery_level: float
    attempts_count: int
    correct_count: int
    current_difficulty: int


class AnalyticsSummary(BaseModel):
    users_count: int
    solved_tasks_count: int
    average_accuracy: float
    average_latency_ms: float
    gamification_events_count: int
