from __future__ import annotations

import csv
import math
import statistics
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = REPO_ROOT / "reports"


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.get_calls = 0
        self.setex_calls = 0
        self.delete_calls = 0

    async def get(self, key: str) -> str | None:
        self.get_calls += 1
        return self.store.get(key)

    async def setex(self, key: str, ttl: int, value: str) -> bool:
        del ttl
        self.setex_calls += 1
        self.store[key] = value
        return True

    async def delete(self, key: str) -> int:
        self.delete_calls += 1
        return 1 if self.store.pop(key, None) is not None else 0

    async def ping(self) -> bool:
        return True

    def clear(self) -> None:
        self.store.clear()
        self.get_calls = 0
        self.setex_calls = 0
        self.delete_calls = 0


def make_test_settings(**overrides: Any) -> SimpleNamespace:
    defaults = {
        "database_url": "sqlite+aiosqlite://",
        "debug": False,
        "log_level": "INFO",
        "content_generation_mode": "template",
        "yandexgpt_api_key": "test-api-key",
        "yandexgpt_iam_token": "",
        "yandexgpt_folder_id": "test-folder",
        "yandexgpt_model": "yandexgpt-lite",
        "yandexgpt_model_uri": "",
        "yandexgpt_few_shot_examples": 2,
        "yandexgpt_base_url": "https://example.invalid/yandexgpt",
        "yandexgpt_timeout_seconds": 0.1,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def percentile(values: list[float], percentile_rank: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (len(sorted_values) - 1) * (percentile_rank / 100)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return sorted_values[lower]
    weight = rank - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def summarize_latencies(
    latencies_seconds: list[float], errors: int = 0
) -> dict[str, float | int]:
    latencies_ms = [value * 1000 for value in latencies_seconds]
    count = len(latencies_ms)
    total = count + errors
    if count:
        mean_ms = statistics.fmean(latencies_ms)
        median_ms = statistics.median(latencies_ms)
        min_ms = min(latencies_ms)
        max_ms = max(latencies_ms)
        std_ms = statistics.stdev(latencies_ms) if count > 1 else 0.0
        margin = 1.96 * std_ms / math.sqrt(count) if count > 1 else 0.0
        ci_low_ms = mean_ms - margin
        ci_high_ms = mean_ms + margin
    else:
        mean_ms = median_ms = min_ms = max_ms = std_ms = ci_low_ms = ci_high_ms = 0.0
    return {
        "requests": total,
        "successes": count,
        "errors": errors,
        "error_rate": errors / total if total else 0.0,
        "mean_ms": mean_ms,
        "median_ms": median_ms,
        "p95_ms": percentile(latencies_ms, 95),
        "p99_ms": percentile(latencies_ms, 99),
        "min_ms": min_ms,
        "max_ms": max_ms,
        "std_ms": std_ms,
        "ci95_low_ms": ci_low_ms,
        "ci95_high_ms": ci_high_ms,
    }


def append_csv_row(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(row.keys()))
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def write_csv_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        if not exists:
            writer.writeheader()
        writer.writerows(rows)


async def benchmark_async(
    operation,
    iterations: int,
    *,
    error_predicate=None,
) -> tuple[list[float], int]:
    latencies: list[float] = []
    errors = 0
    for _ in range(iterations):
        started = perf_counter()
        try:
            result = await operation()
            elapsed = perf_counter() - started
            if error_predicate is not None and error_predicate(result):
                errors += 1
            else:
                latencies.append(elapsed)
        except Exception:
            errors += 1
    return latencies, errors


def benchmark_sync(operation, iterations: int) -> list[float]:
    latencies: list[float] = []
    for _ in range(iterations):
        started = perf_counter()
        operation()
        latencies.append(perf_counter() - started)
    return latencies
