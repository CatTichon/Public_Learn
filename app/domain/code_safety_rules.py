import ast


class CodeSafetyError(ValueError):
    """Raised when submitted code uses disallowed Python constructs."""


FORBIDDEN_IMPORTS = {
    "asyncio",
    "builtins",
    "ctypes",
    "multiprocessing",
    "os",
    "pathlib",
    "pickle",
    "shutil",
    "socket",
    "subprocess",
    "sys",
    "threading",
}

FORBIDDEN_CALLS = {
    "__import__",
    "compile",
    "eval",
    "exec",
    "globals",
    "input",
    "locals",
    "open",
}


def validate_python_code_safety(code: str) -> None:
    """Reject obvious dangerous operations before executing learner code."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise CodeSafetyError(f"Синтаксическая ошибка: {exc.msg}") from exc

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_name = alias.name.split(".", 1)[0]
                if root_name in FORBIDDEN_IMPORTS:
                    raise CodeSafetyError(f"Запрещён импорт модуля {root_name}")
        elif isinstance(node, ast.ImportFrom):
            root_name = (node.module or "").split(".", 1)[0]
            if root_name in FORBIDDEN_IMPORTS:
                raise CodeSafetyError(f"Запрещён импорт модуля {root_name}")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_CALLS:
                raise CodeSafetyError(f"Запрещён вызов функции {node.func.id}")
