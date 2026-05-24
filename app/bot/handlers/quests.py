from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.services.quest_service import QuestService

router = Router()


@router.message(Command("quests"))
@router.message(lambda m: m.text == "Квесты")
async def quests(message: Message, user_profile, session) -> None:
    lines = ["Активные квесты:"]
    for uq in await QuestService(session).list_user_quests(user_profile.id):
        status = (
            "выполнен" if uq.is_completed else f"{uq.progress}/{uq.quest.target_value}"
        )
        lines.append(f"- {uq.quest.title}: {status}, награда {uq.quest.xp_reward} XP")
    await message.answer("\n".join(lines))
