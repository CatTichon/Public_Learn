from types import SimpleNamespace

from app.services.answer_check_service import AnswerCheckService


def test_numeric_answer_accepts_comma_and_tolerance():
    service = AnswerCheckService()
    assert service.check_numeric_answer("30.00", "30,005")
    assert not service.check_numeric_answer("30", "31")


def test_text_answer_normalization():
    service = AnswerCheckService()
    assert service.check_text_answer(" Линейное уравнение ", "линейное   уравнение")


def test_single_choice_check():
    service = AnswerCheckService()
    task = SimpleNamespace(task_type="single_choice", correct_answer="24")
    assert service.check_answer(task, "24")
