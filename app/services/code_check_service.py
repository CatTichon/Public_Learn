import ast
import multiprocessing
from dataclasses import dataclass, field
from multiprocessing import Queue
from typing import Any

from app.domain.code_safety_rules import CodeSafetyError, validate_python_code_safety


@dataclass(slots=True)
class CodeCheckResult:
    is_correct: bool
    feedback: str
    passed_tests: int = 0
    total_tests: int = 0
    errors: list[str] = field(default_factory=list)


class CodeCheckService:
    timeout_seconds = 2.0

    def check_code(self, task, user_code: str) -> CodeCheckResult:
        test_cases = self._normalize_test_cases(task.test_cases)
        if not test_cases:
            return CodeCheckResult(False, "Для задания не настроены тесты.")

        try:
            validate_python_code_safety(user_code)
        except CodeSafetyError as exc:
            safety_errors = [str(exc)]
            return CodeCheckResult(
                False,
                "Код содержит запрещённые конструкции: " + "; ".join(safety_errors),
                total_tests=len(test_cases),
                errors=safety_errors,
            )

        function_name = self._detect_function_name(user_code, test_cases)
        if function_name is None:
            return CodeCheckResult(
                False,
                "Не найдена функция для проверки. Объяви функцию как в шаблоне задания.",
                total_tests=len(test_cases),
            )

        queue: Queue = multiprocessing.Queue()
        process = multiprocessing.Process(
            target=_run_code_tests,
            args=(user_code, function_name, test_cases, queue),
        )
        process.start()
        process.join(self.timeout_seconds)
        if process.is_alive():
            process.terminate()
            process.join()
            return CodeCheckResult(
                False,
                "Превышено время выполнения кода.",
                total_tests=len(test_cases),
            )

        if queue.empty():
            return CodeCheckResult(
                False,
                "Не удалось получить результат проверки кода.",
                total_tests=len(test_cases),
            )

        payload = queue.get()
        return CodeCheckResult(
            is_correct=payload["is_correct"],
            feedback=payload["feedback"],
            passed_tests=payload["passed_tests"],
            total_tests=payload["total_tests"],
            errors=payload.get("errors", []),
        )

    def _detect_function_name(
        self, user_code: str, test_cases: list[dict[str, Any]]
    ) -> str | None:
        explicit_name = next(
            (
                case.get("function_name")
                for case in test_cases
                if case.get("function_name")
            ),
            None,
        )
        if explicit_name:
            return explicit_name
        tree = ast.parse(user_code)
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                return node.name
        return None

    def _normalize_test_cases(self, raw_test_cases) -> list[dict[str, Any]]:
        if not raw_test_cases:
            return []
        if isinstance(raw_test_cases, dict):
            function_name = raw_test_cases.get("function_name")
            tests = raw_test_cases.get("tests", [])
            return [
                {
                    **case,
                    "function_name": case.get("function_name") or function_name,
                }
                for case in tests
            ]
        return raw_test_cases


def _run_code_tests(
    user_code: str,
    function_name: str,
    test_cases: list[dict[str, Any]],
    queue: Queue,
) -> None:
    namespace: dict[str, Any] = {"__builtins__": _safe_builtins()}
    try:
        exec(compile(user_code, "<student_code>", "exec"), namespace)
        func = namespace.get(function_name)
        if not callable(func):
            queue.put(
                {
                    "is_correct": False,
                    "feedback": f"Функция {function_name} не найдена.",
                    "passed_tests": 0,
                    "total_tests": len(test_cases),
                }
            )
            return

        passed = 0
        errors = []
        for index, case in enumerate(test_cases, start=1):
            args = case.get("input", [])
            expected = case.get("expected")
            if not isinstance(args, list):
                args = [args]
            actual = func(*args)
            if actual == expected:
                passed += 1
                continue
            errors.append(
                f"Тест {index}: вход {args}, ожидалось {expected!r}, получено {actual!r}"
            )

        queue.put(
            {
                "is_correct": passed == len(test_cases),
                "feedback": (
                    "Все тесты пройдены." if passed == len(test_cases) else errors[0]
                ),
                "passed_tests": passed,
                "total_tests": len(test_cases),
                "errors": errors,
            }
        )
    except Exception as exc:
        queue.put(
            {
                "is_correct": False,
                "feedback": f"Ошибка выполнения: {type(exc).__name__}: {exc}",
                "passed_tests": 0,
                "total_tests": len(test_cases),
                "errors": [str(exc)],
            }
        )


def _safe_builtins() -> dict[str, Any]:
    return {
        "abs": abs,
        "all": all,
        "any": any,
        "bool": bool,
        "dict": dict,
        "enumerate": enumerate,
        "float": float,
        "int": int,
        "len": len,
        "list": list,
        "max": max,
        "min": min,
        "range": range,
        "round": round,
        "set": set,
        "str": str,
        "sum": sum,
        "tuple": tuple,
    }
