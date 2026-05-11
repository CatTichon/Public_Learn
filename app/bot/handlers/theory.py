from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.repositories.topics import TopicRepository

router = Router()


@router.message(Command("theory"))
@router.message(lambda m: m.text == "Теория")
async def theory(message: Message, user_profile, session) -> None:
    if not user_profile.selected_topic_id:
        await message.answer("Сначала выбери тему через /topics, затем открой теорию.")
        return

    topic = await TopicRepository(session).get(user_profile.selected_topic_id)
    if topic is None:
        await message.answer("Выбранная тема не найдена. Попробуй выбрать тему заново.")
        return

    await message.answer(f"{topic.title}\n\n{topic.description}")
