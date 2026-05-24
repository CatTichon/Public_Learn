from __future__ import annotations

import csv
from collections import defaultdict
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"


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


def average_series(
    rows: list[dict[str, str]], x_key: str, y_key: str, series_key: str
) -> dict[str, list[tuple[float, float]]]:
    grouped: dict[str, dict[float, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in rows:
        x_value = as_float(row.get(x_key))
        y_value = as_float(row.get(y_key))
        series_name = row.get(series_key, "")
        if x_value is None or y_value is None or not series_name:
            continue
        grouped[series_name][x_value].append(y_value)
    result: dict[str, list[tuple[float, float]]] = {}
    for series_name, points in grouped.items():
        result[series_name] = [
            (x_value, sum(values) / len(values))
            for x_value, values in sorted(points.items())
        ]
    return result


def average_bars(
    rows: list[dict[str, str]], label_key: str, value_key: str
) -> list[tuple[str, float]]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        label = row.get(label_key, "")
        value = as_float(row.get(value_key))
        if label and value is not None:
            grouped[label].append(value)
    return sorted(
        (label, sum(values) / len(values)) for label, values in grouped.items()
    )


def line_chart(
    path: Path,
    title: str,
    x_label: str,
    y_label: str,
    series: dict[str, list[tuple[float, float]]],
) -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    width, height = 900, 520
    left, right, top, bottom = 80, 40, 60, 70
    plot_width = width - left - right
    plot_height = height - top - bottom
    colors = ["#2563eb", "#dc2626", "#16a34a", "#9333ea", "#ea580c", "#0891b2"]

    all_points = [point for values in series.values() for point in values]
    if not all_points:
        return
    x_values = [point[0] for point in all_points]
    y_values = [point[1] for point in all_points]
    x_min, x_max = min(x_values), max(x_values)
    y_min, y_max = min(y_values), max(y_values)
    if x_min == x_max:
        x_max += 1
    if y_min == y_max:
        y_max += 1

    def to_x(value: float) -> float:
        return left + ((value - x_min) / (x_max - x_min)) * plot_width

    def to_y(value: float) -> float:
        return top + plot_height - ((value - y_min) / (y_max - y_min)) * plot_height

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        f'<text x="{width / 2}" y="30" text-anchor="middle" font-size="20">{escape(title)}</text>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}" stroke="#111827" />',
        f'<line x1="{left}" y1="{top + plot_height}" x2="{left + plot_width}" y2="{top + plot_height}" stroke="#111827" />',
        f'<text x="{width / 2}" y="{height - 20}" text-anchor="middle" font-size="14">{escape(x_label)}</text>',
        f'<text x="20" y="{height / 2}" transform="rotate(-90 20,{height / 2})" text-anchor="middle" font-size="14">{escape(y_label)}</text>',
    ]

    for index, (series_name, points) in enumerate(series.items()):
        color = colors[index % len(colors)]
        polyline = " ".join(f"{to_x(x):.2f},{to_y(y):.2f}" for x, y in points)
        parts.append(
            f'<polyline fill="none" stroke="{color}" stroke-width="3" points="{polyline}" />'
        )
        for x_value, y_value in points:
            parts.append(
                f'<circle cx="{to_x(x_value):.2f}" cy="{to_y(y_value):.2f}" r="4" fill="{color}" />'
            )
        legend_y = top + 20 + index * 22
        parts.append(
            f'<rect x="{width - 210}" y="{legend_y - 10}" width="14" height="14" fill="{color}" />'
        )
        parts.append(
            f'<text x="{width - 190}" y="{legend_y + 1}" font-size="13">{escape(series_name)}</text>'
        )

    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def bar_chart(
    path: Path, title: str, y_label: str, data: list[tuple[str, float]]
) -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    width, height = 980, 540
    left, right, top, bottom = 80, 40, 60, 120
    plot_width = width - left - right
    plot_height = height - top - bottom
    colors = ["#2563eb", "#16a34a", "#dc2626", "#9333ea", "#ea580c", "#0891b2"]
    if not data:
        return
    max_value = max(value for _, value in data) or 1.0
    bar_width = plot_width / max(len(data), 1)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        f'<text x="{width / 2}" y="30" text-anchor="middle" font-size="20">{escape(title)}</text>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}" stroke="#111827" />',
        f'<line x1="{left}" y1="{top + plot_height}" x2="{left + plot_width}" y2="{top + plot_height}" stroke="#111827" />',
        f'<text x="20" y="{height / 2}" transform="rotate(-90 20,{height / 2})" text-anchor="middle" font-size="14">{escape(y_label)}</text>',
    ]

    for index, (label, value) in enumerate(data):
        color = colors[index % len(colors)]
        x = left + index * bar_width + bar_width * 0.15
        actual_width = bar_width * 0.7
        bar_height = (value / max_value) * plot_height
        y = top + plot_height - bar_height
        parts.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{actual_width:.2f}" height="{bar_height:.2f}" fill="{color}" />'
        )
        parts.append(
            f'<text x="{x + actual_width / 2:.2f}" y="{y - 6:.2f}" text-anchor="middle" font-size="11">{value:.2f}</text>'
        )
        parts.append(
            f'<text x="{x + actual_width / 2:.2f}" y="{top + plot_height + 20}" text-anchor="middle" font-size="11" transform="rotate(25 {x + actual_width / 2:.2f},{top + plot_height + 20})">{escape(label)}</text>'
        )

    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def build_adaptive_chart() -> None:
    rows = read_rows(REPORTS_DIR / "experiments" / "adaptive_vs_linear.csv")
    series = average_series(rows, "attempt", "mastery_level", "mode")
    line_chart(
        FIGURES_DIR / "accuracy_adaptation_vs_attempt.svg",
        "Adaptive vs linear mastery by attempt",
        "Attempt",
        "Mastery level",
        series,
    )


def build_generation_chart() -> None:
    rows = [
        row
        for row in read_rows(
            REPORTS_DIR / "performance" / "content_generation_latency.csv"
        )
        if row.get("mean_ms")
    ]
    data = average_bars(rows, "mode", "mean_ms")
    bar_chart(
        FIGURES_DIR / "generation_latency_by_mode.svg",
        "Generation latency by mode",
        "Mean latency, ms",
        data,
    )


def build_load_chart() -> None:
    rows = read_rows(REPORTS_DIR / "performance" / "load_test.csv")
    series = average_series(rows, "virtual_users", "mean_ms", "test_name")
    line_chart(
        FIGURES_DIR / "response_time_under_load.svg",
        "Response time under load",
        "Virtual users",
        "Mean latency, ms",
        series,
    )


def build_answer_check_chart() -> None:
    rows = [
        row
        for row in read_rows(REPORTS_DIR / "performance" / "answer_check_latency.csv")
        if row.get("mean_ms")
    ]
    data = average_bars(rows, "check_type", "mean_ms")
    bar_chart(
        FIGURES_DIR / "local_check_vs_external_api_latency.svg",
        "Local check vs external API latency",
        "Mean latency, ms",
        data,
    )


def main() -> None:
    build_adaptive_chart()
    build_generation_chart()
    build_load_chart()
    build_answer_check_chart()
    print(f"Charts saved to {FIGURES_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
