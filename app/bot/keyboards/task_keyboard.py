from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.topic_catalog import partition_school_and_ege


def options_keyboard(task_id: int, options: list[str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=o, callback_data=f"answer:{task_id}:{o}")]
            for o in options
        ]
    )


def topic_sections_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Школьная математика",
                    callback_data="topics:section:school",
                )
            ],
            [
                InlineKeyboardButton(
                    text="ЕГЭ профиль (по номерам)",
                    callback_data="topics:section:ege",
                )
            ],
        ]
    )


def topics_keyboard(topics) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.title, callback_data=f"topic:{t.id}")]
            for t in topics
        ]
    )


def topics_keyboard_with_back(topics) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=t.title, callback_data=f"topic:{t.id}")]
        for t in topics
    ]
    rows.append(
        [
            InlineKeyboardButton(
                text="« К разделам", callback_data="topics:root"
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def topics_section_from_list(all_topics, section: str) -> InlineKeyboardMarkup:
    school, ege = partition_school_and_ege(list(all_topics))
    chosen = school if section == "school" else ege
    return topics_keyboard_with_back(chosen)
