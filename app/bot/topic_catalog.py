"""Helpers for grouping bot-visible topics (school vs ЕГЭ) and ordering."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.topic import Topic

_EGE_NUM = re.compile(r"ЕГЭ\s*профиль\s*№\s*(\d+)", re.IGNORECASE)


def is_ege_profile_topic_title(title: str | None) -> bool:
    if not title:
        return False
    return "ЕГЭ профиль №" in title or bool(_EGE_NUM.search(title))


def partition_school_and_ege(topics: list[Topic]) -> tuple[list[Topic], list[Topic]]:
    school: list[Topic] = []
    ege: list[Topic] = []
    for t in topics:
        if is_ege_profile_topic_title(t.title):
            ege.append(t)
        else:
            school.append(t)
    school.sort(key=lambda x: (x.title or "").lower())
    ege.sort(
        key=lambda x: (
            _ege_number_from_title(x.title),
            (x.title or "").lower(),
        )
    )
    return school, ege


def _ege_number_from_title(title: str | None) -> int:
    if not title:
        return 999
    m = _EGE_NUM.search(title)
    return int(m.group(1)) if m else 999
