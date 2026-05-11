import json
from pathlib import Path


def test_ege_dataset_has_topics_and_tasks():
    dataset = json.loads(
        Path("data/ege_profile_math_2026.json").read_text(encoding="utf-8")
    )

    assert dataset["exam"] == "ЕГЭ 2026, математика, профильный уровень"
    assert len(dataset["topics"]) == 19
    assert len(dataset["tasks_by_topic"]) == 19


def test_ege_dataset_tasks_match_topic_titles():
    dataset = json.loads(
        Path("data/ege_profile_math_2026.json").read_text(encoding="utf-8")
    )
    titles = {topic["title"] for topic in dataset["topics"]}

    assert set(dataset["tasks_by_topic"]) == titles
    for tasks in dataset["tasks_by_topic"].values():
        assert len(tasks) >= 3
        for task in tasks:
            task_type, difficulty, question, answer, _options, explanation = task
            assert task_type == "numeric_answer"
            assert 1 <= difficulty <= 5
            assert question
            assert answer
            assert explanation
