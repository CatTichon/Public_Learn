from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.services.analytics_service import AnalyticsService

router = Router()


@router.message(Command("profile"))
@router.message(lambda m: m.text == "Профиль")
async def profile(message: Message, user_profile, session) -> None:
    stats = await AnalyticsService(session).user_stats(user_profile.id)
    await message.answer(
        f"Профиль: {user_profile.first_name or user_profile.username or user_profile.telegram_id}\nУровень: {user_profile.level}\nXP: {user_profile.xp}\nСерия: {user_profile.current_streak} (макс. {user_profile.max_streak})\nРешено: {stats.total_tasks}, верно: {stats.correct_answers}, точность: {stats.accuracy:.0%}"
    )


@router.message(Command("stats"))
@router.message(lambda m: m.text == "Статистика")
async def stats(message: Message, user_profile, session) -> None:
    progress = await AnalyticsService(session).progress(user_profile.id)
    lines = ["Прогресс по темам:"] + [
        f"- {p.topic_title}: {p.mastery_level:.0%}, сложность {p.current_difficulty}/5"
        for p in progress
    ]
    await message.answer("\n".join(lines) if len(lines) > 1 else "Пока нет статистики.")
