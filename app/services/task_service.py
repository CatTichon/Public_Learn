from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.logs import TaskLogRepository
from app.repositories.tasks import TaskRepository
from app.services.adaptive_service import AdaptiveService
from app.services.answer_check_service import AnswerCheckService
from app.services.code_check_service import CodeCheckService
from app.services.gamification_service import GamificationService


class TaskService:
    def __init__(self, session: AsyncSession, redis: Redis | None = None):
        self.session = session
        self.tasks = TaskRepository(session)
        self.task_logs = TaskLogRepository(session)
        self.answer_checker = AnswerCheckService()
        self.code_checker = CodeCheckService()
        self.adaptive = AdaptiveService(session, redis)
        self.gamification = GamificationService(session)

    async def next_task(self, user_id: int, topic_id: int):
        return await self.adaptive.select_next_task(user_id, topic_id)

    async def answer_task(
        self, user_id: int, task_id: int, answer: str, answer_time_seconds: float
    ):
        task = await self.tasks.get(task_id)
        if task is None:
            raise ValueError("Task not found")
        code_result = None
        if task.task_type == "code_answer":
            code_result = self.code_checker.check_code(task, answer)
            is_correct = code_result.is_correct
        else:
            is_correct = self.answer_checker.check_answer(task, answer)
        await self.task_logs.create(
            user_id=user_id,
            task_id=task.id,
            topic_id=task.topic_id,
            task_type=task.task_type,
            difficulty=task.difficulty,
            user_answer=answer,
            is_correct=is_correct,
            answer_time_seconds=answer_time_seconds,
        )
        mastery = await self.adaptive.update_mastery_after_answer(
            user_id, task.topic_id, is_correct, answer_time_seconds, task.difficulty
        )
        xp = self.gamification.calculate_answer_xp(is_correct, task.difficulty)
        xp_result = await self.gamification.add_xp(user_id, xp, "Ответ на задание")
        await self.gamification.update_streak(user_id)
        completed = await self.gamification.update_quests(
            user_id, "task_completed", task.topic_id
        )
        unlocked = await self.gamification.check_achievements(user_id)
        await self.gamification.log_gamification_event(
            user_id,
            "correct_answer" if is_correct else "wrong_answer",
            xp,
            "Результат проверки ответа",
        )
        feedback = self._build_feedback(task, is_correct, code_result)
        return {
            "task": task,
            "is_correct": is_correct,
            "xp_gained": xp_result.xp_gained,
            "new_level": xp_result.new_level,
            "mastery": mastery,
            "completed_quests": completed,
            "unlocked_achievements": unlocked,
            "code_result": code_result,
            "feedback": feedback,
        }

    def _build_feedback(self, task, is_correct: bool, code_result) -> str:
        if code_result is not None:
            return code_result.feedback
        if is_correct:
            return "Ответ верный."
        if task.explanation:
            return task.explanation
        return f"Правильный ответ: {task.correct_answer}."
