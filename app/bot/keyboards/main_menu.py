from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Получить задание"),
                KeyboardButton(text="Выбрать тему"),
            ],
            [KeyboardButton(text="Профиль"), KeyboardButton(text="Квесты")],
            [
                KeyboardButton(text="Достижения"),
                KeyboardButton(text="Статистика"),
                KeyboardButton(text="Теория"),
            ],
        ],
        resize_keyboard=True,
    )
