from __future__ import annotations

import csv
import math
import statistics
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = 10
TEST_TARGETS = [
    "tests/performance/test_api_response_time.py",
    "tests/performance/test_content_generation_latency.py",
    "tests/performance/test_cache_vs_generation.py",
    "tests/performance/test_answer_check_latency.py",
    "tests/performance/test_load_api.py",
    "tests/experiments/test_adaptive_vs_linear.py",
]
REPORT_FILES = [
    ROOT / "reports" / "performance" / "api_response_time.csv",
    ROOT / "reports" / "performance" / "content_generation_latency.csv",
    ROOT / "reports" / "performance" / "cache_vs_generation.csv",
    ROOT / "reports" / "performance" / "answer_check_latency.csv",
    ROOT / "reports" / "performance" / "load_test.csv",
    ROOT / "reports" / "experiments" / "adaptive_vs_linear.csv",
]
SUMMARY_PATH = ROOT / "reports" / "experiments" / "experiment_summary.csv"


def percentile(values: list[float], percentile_rank: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (len(sorted_values) - 1) * percentile_rank / 100
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return sorted_values[lower]
    weight = rank - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def summarize(values: list[float]) -> dict[str, float | int]:
    count = len(values)
    mean_value = statistics.fmean(values) if values else 0.0
    median_value = statistics.median(values) if values else 0.0
    min_value = min(values) if values else 0.0
    max_value = max(values) if values else 0.0
    std_value = statistics.stdev(values) if count > 1 else 0.0
    margin = 1.96 * std_value / math.sqrt(count) if count > 1 else 0.0
    return {
        "samples": count,
        "mean": mean_value,
        "median": median_value,
        "p95": percentile(values, 95),
        "p99": percentile(values, 99),
        "std": std_value,
        "min": min_value,
        "max": max_value,
        "ci95_low": mean_value - margin,
        "ci95_high": mean_value + margin,
    }


def as_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def append_summary_rows(
    summary_rows: list[dict[str, object]],
    rows: list[dict[str, str]],
    *,
    dataset: str,
    group_keys: tuple[str, ...],
    metric_keys: tuple[str, ...],
) -> None:
    grouped: dict[tuple[str, ...], dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in rows:
        group = tuple(row.get(key, "") for key in group_keys)
        for metric_key in metric_keys:
            value = as_float(row.get(metric_key))
            if value is not None:
                grouped[group][metric_key].append(value)

    for group, metrics in grouped.items():
        group_label = " | ".join(part for part in group if part)
        for metric_key, values in metrics.items():
            summary_rows.append(
                {
                    "dataset": dataset,
                    "group": group_label,
                    "metric": metric_key,
                    **summarize(values),
                }
            )


def summarize_reports() -> list[dict[str, object]]:
    summary_rows: list[dict[str, object]] = []

    append_summary_rows(
        summary_rows,
        read_rows(REPORT_FILES[0]),
        dataset="api_response_time",
        group_keys=("test_name",),
        metric_keys=("mean_ms", "p95_ms", "p99_ms", "error_rate"),
    )
    append_summary_rows(
        summary_rows,
        [row for row in read_rows(REPORT_FILES[1]) if row.get("mean_ms")],
        dataset="content_generation_latency",
        group_keys=("test_name", "mode", "scenario"),
        metric_keys=("mean_ms", "p95_ms", "error_rate"),
    )
    append_summary_rows(
        summary_rows,
        read_rows(REPORT_FILES[2]),
        dataset="cache_vs_generation",
        group_keys=("test_name",),
        metric_keys=(
            "cached_mean_ms",
            "template_generation_mean_ms",
            "database_mean_ms",
            "hit_rate",
        ),
    )
    append_summary_rows(
        summary_rows,
        read_rows(REPORT_FILES[3]),
        dataset="answer_check_latency",
        group_keys=("test_name", "check_type"),
        metric_keys=(
            "mean_ms",
            "p95_ms",
            "error_rate",
            "local_mean_ms",
            "external_mean_ms",
        ),
    )
    append_summary_rows(
        summary_rows,
        read_rows(REPORT_FILES[4]),
        dataset="load_test",
        group_keys=("test_name", "virtual_users"),
        metric_keys=("mean_ms", "p95_ms", "p99_ms", "throughput_rps", "error_rate"),
    )

    adaptive_rows = read_rows(REPORT_FILES[5])
    max_attempt = 0
    for row in adaptive_rows:
        attempt_value = as_float(row.get("attempt"))
        if attempt_value is not None:
            max_attempt = max(max_attempt, int(attempt_value))
    final_attempt_rows = [
        row
        for row in adaptive_rows
        if int(float(row.get("attempt", "0"))) == max_attempt
    ]
    append_summary_rows(
        summary_rows,
        final_attempt_rows,
        dataset="adaptive_vs_linear",
        group_keys=("mode", "user_type"),
        metric_keys=("mastery_level",),
    )
    append_summary_rows(
        summary_rows,
        adaptive_rows,
        dataset="adaptive_vs_linear",
        group_keys=("mode", "user_type"),
        metric_keys=("adaptation_correct",),
    )
    return summary_rows


def write_summary_csv(rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SUMMARY_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def print_table(rows: list[dict[str, object]]) -> None:
    if not rows:
        print("No summary rows were generated.")
        return
    columns = ["dataset", "group", "metric", "samples", "mean", "median", "p95", "p99"]
    printable = [{key: row.get(key, "") for key in columns} for row in rows]
    widths = {
        column: max(len(column), *(len(str(row[column])) for row in printable))
        for column in columns
    }
    separator = " | ".join("-" * widths[column] for column in columns)
    print(" | ".join(column.ljust(widths[column]) for column in columns))
    print(separator)
    for row in printable:
        print(" | ".join(str(row[column]).ljust(widths[column]) for column in columns))


def clear_reports() -> None:
    for report in REPORT_FILES:
        if report.exists():
            report.unlink()
    if SUMMARY_PATH.exists():
        SUMMARY_PATH.unlink()


def run_targets() -> None:
    for run_index in range(1, RUNS + 1):
        print(f"=== Run {run_index}/{RUNS} ===")
        for target in TEST_TARGETS:
            print(f"Running {target}")
            subprocess.run(
                [sys.executable, "-m", "pytest", target, "-q"],
                cwd=ROOT,
                check=True,
            )


def main() -> None:
    clear_reports()
    run_targets()
    summary_rows = summarize_reports()
    write_summary_csv(summary_rows)
    print()
    print_table(summary_rows)
    print()
    print(f"Summary CSV saved to {SUMMARY_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
