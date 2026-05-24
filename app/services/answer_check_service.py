from decimal import Decimal, InvalidOperation
from typing import Protocol


class AnswerableTask(Protocol):
    task_type: str
    correct_answer: str
    test_cases: list[dict] | None


class AnswerCheckService:
    tolerance = Decimal("0.01")

    def normalize_answer(self, answer: str) -> str:
        return " ".join(str(answer).strip().lower().split())

    def check_numeric_answer(self, correct_answer: str, user_answer: str) -> bool:
        try:
            correct = Decimal(self.normalize_answer(correct_answer).replace(",", "."))
            actual = Decimal(self.normalize_answer(user_answer).replace(",", "."))
        except (InvalidOperation, ValueError):
            return False
        return abs(correct - actual) <= self.tolerance

    def check_text_answer(self, correct_answer: str, user_answer: str) -> bool:
        return self.normalize_answer(correct_answer) == self.normalize_answer(
            user_answer
        )

    def check_answer(self, task: AnswerableTask, user_answer: str) -> bool:
        if task.task_type == "code_answer":
            from app.services.code_check_service import CodeCheckService

            return CodeCheckService().check_code(task, user_answer).is_correct
        if task.task_type == "numeric_answer":
            return self.check_numeric_answer(task.correct_answer, user_answer)
        return self.check_text_answer(task.correct_answer, user_answer)
