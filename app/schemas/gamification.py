from pydantic import BaseModel, ConfigDict


class XpResult(BaseModel):
    xp_gained: int
    old_level: int
    new_level: int
    leveled_up: bool


class AchievementRead(BaseModel):
    code: str
    title: str
    description: str
    condition_type: str
    condition_value: int
    xp_reward: int
    unlocked: bool = False
    model_config = ConfigDict(from_attributes=True)
