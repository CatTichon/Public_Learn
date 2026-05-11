from aiogram import F,Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.main_menu import main_menu_keyboard
from app.bot.keyboards.task_keyboard import (
    topic_sections_keyboard,
    topics_section_from_list,
)
from app.repositories.topics import TopicRepository

router = Router()


@router.message(Command("start"))
async def start(message: Message, user_profile, session) -> None:
    await message.answer(
        f"Привет! Это адаптивный учебный бот.\n\nЯ подбираю задания по прогрессу, начисляю XP, уровни, серии, достижения и квесты.\nСейчас у тебя уровень {user_profile.level}, XP: {user_profile.xp}, серия: {user_profile.current_streak}.\n\nВ «Выбрать тему» есть раздел ЕГЭ профиль (номера 1–19) и школьные темы. Затем запроси задание.",
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(
        "Команды: /topics, /task, /profile, /quests, /achievements, /stats, /theory"
    )


@router.message(Command("topics"))
@router.message(lambda m: m.text == "Выбрать тему")
async def topics(message: Message, session) -> None:
    await message.answer(
        "Выбери раздел: школьная математика или задания ЕГЭ профиль (по номерам и темам).",
        reply_markup=topic_sections_keyboard(),
    )


@router.callback_query(F.data == "topics:root")
async def topics_root(callback: CallbackQuery, session) -> None:
    await callback.message.edit_text(
        "Выбери раздел: школьная математика или задания ЕГЭ профиль (по номерам и темам).",
        reply_markup=topic_sections_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("topics:section:"))
async def topics_section(callback: CallbackQuery, session) -> None:
    section = callback.data.split(":", 2)[2]
    if section not in ("school", "ege"):
        await callback.answer("Неизвестный раздел", show_alert=True)
        return
    all_topics = await TopicRepository(session).list_active()
    label = (
        "Школьная математика — выбери тему:"
        if section == "school"
        else "ЕГЭ профиль — выбери номер задания (тему):"
    )
    await callback.message.edit_text(
        label,
        reply_markup=topics_section_from_list(all_topics, section),
    )
    await callback.answer()