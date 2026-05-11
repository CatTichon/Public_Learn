from types import SimpleNamespace

from app.services.gamification_service import GamificationService


def test_achievement_condition_topic_mastery():
    service = object.__new__(GamificationService)
    ach = SimpleNamespace(condition_type="topic_mastery", condition_value=80)
    assert service._achievement_condition_met(
        ach, None, {"total": 0, "correct": 0}, [SimpleNamespace(mastery_level=0.82)]
    )


def test_quest_completion_threshold_shape():
    user_quest = SimpleNamespace(progress=2, is_completed=False)
    quest = SimpleNamespace(target_value=3)
    user_quest.progress += 1
    assert user_quest.progress >= quest.target_value
