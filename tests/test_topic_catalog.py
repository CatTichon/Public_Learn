import json
from pathlib import Path
from types import SimpleNamespace

from app.bot.topic_catalog import is_ege_profile_topic_title, partition_school_and_ege


def test_is_ege_profile_topic_title():
    assert is_ege_profile_topic_title("ЕГЭ профиль №1. Планиметрия")
    assert not is_ege_profile_topic_title("Арифметика")
    assert is_ege_profile_topic_title(None) is False


def test_partition_orders_ege_by_number():
    dataset = json.loads(
        Path("data/ege_profile_math_2026.json").read_text(encoding="utf-8")
    )
    titles = [t["title"] for t in dataset["topics"]]
    topics = [SimpleNamespace(title=title) for title in reversed(titles)]
    school, ege = partition_school_and_ege(
        topics + [SimpleNamespace(title="Геометрия"), SimpleNamespace(title="Арифметика")]
    )
    assert {t.title for t in school} == {"Арифметика", "Геометрия"}
    nums = []
    for t in ege:
        assert "ЕГЭ профиль №" in t.title
        n = int(t.title.split("№")[1].split(".")[0].strip())
        nums.append(n)
    assert nums == sorted(nums)
