from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.repositories.gamification import AchievementRepository

router = Router()


@router.message(Command("achievements"))
@router.message(lambda m: m.text == "Достижения")
async def achievements(message: Message, user_profile, session) -> None:
    repo = AchievementRepository(session)
    lines = ["Достижения:"]
    for ach in await repo.list_all():
        lines.append(
            f"{'✓' if await repo.user_has(user_profile.id, ach.id) else '•'} {ach.title}: {ach.description} (+{ach.xp_reward} XP)"
        )
    await message.answer("\n".join(lines))
