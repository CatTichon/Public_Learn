from app.services.code_check_service import CodeCheckService


class FakeTask:
    def __init__(self, test_cases):
        self.test_cases = test_cases


def test_code_answer_passes_tests():
    service = CodeCheckService()
    result = service.check_code(
        FakeTask(
            {
                "function_name": "add",
                "tests": [
                    {"input": [2, 3], "expected": 5},
                    {"input": [-1, 1], "expected": 0},
                ],
            }
        ),
        "def add(a, b):\n    return a + b",
    )

    assert result.is_correct
    assert "пройдены" in result.feedback


def test_code_answer_supports_plain_list_tests():
    service = CodeCheckService()
    result = service.check_code(
        FakeTask(
            [
                {"function_name": "add", "input": [2, 3], "expected": 5},
                {"function_name": "add", "input": [-1, 1], "expected": 0},
            ]
        ),
        "def add(a, b):\n    return a + b",
    )

    assert result.is_correct


def test_code_answer_reports_failed_test():
    service = CodeCheckService()
    result = service.check_code(
        FakeTask(
            {
                "function_name": "add",
                "tests": [{"input": [2, 3], "expected": 5}],
            }
        ),
        "def add(a, b):\n    return a - b",
    )

    assert not result.is_correct
    assert "Тест 1" in result.feedback


def test_code_answer_blocks_imports():
    service = CodeCheckService()
    result = service.check_code(
        FakeTask(
            {
                "function_name": "add",
                "tests": [{"input": [1, 2], "expected": 3}],
            }
        ),
        "import os\ndef add(a, b):\n    return a + b",
    )

    assert not result.is_correct
    assert "импорт" in result.feedback
