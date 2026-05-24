from pydantic import BaseModel, ConfigDict


class QuestRead(BaseModel):
    id: int
    code: str
    title: str
    description: str
    quest_type: str
    target_value: int
    xp_reward: int
    topic_id: int | None
    model_config = ConfigDict(from_attributes=True)


class UserQuestRead(BaseModel):
    quest: QuestRead
    progress: int
    is_completed: bool
    model_config = ConfigDict(from_attributes=True)
