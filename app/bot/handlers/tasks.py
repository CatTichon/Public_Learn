import time

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.task_keyboard import options_keyboard
from app.core.redis import get_redis
from app.services.task_service import TaskService
from app.services.user_service import UserService

router = Router()
MENU_TEXTS = {
    "Получить задание",
    "Выбрать тему",
    "Профиль",
    "Квесты",
    "Достижения",
    "Статистика",
    "Теория",
}


@router.callback_query(F.data.startswith("topic:"))
async def select_topic(callback: CallbackQuery, user_profile, session) -> None:
    topic_id = int(callback.data.split(":", 1)[1])
    topic = await UserService(session).select_topic(user_profile.id, topic_id)
    await callback.message.answer(
        f"Тема выбрана: {topic.title}. Теперь можно получить первое задание."
    )
    await callback.answer()


@router.message(Command("task"))
@router.message(lambda m: m.text == "Получить задание")
async def get_task(message: Message, user_profile, session) -> None:
    if not user_profile.selected_topic_id:
        await message.answer("Сначала выбери тему командой /topics.")
        return
    redis = None
    async for client in get_redis():
        redis = client
        break
    task = await TaskService(session, redis).next_task(
        user_profile.id, user_profile.selected_topic_id
    )
    await session.commit()
    if redis:
        await redis.setex(
            f"current_task:{user_profile.id}", 3600, f"{task.id}:{time.time()}"
        )
    if task.task_type == "single_choice" and task.options:
        await message.answer(
            f"Сложность {task.difficulty}/5\n{task.question_text}",
            reply_markup=options_keyboard(task.id, task.options),
        )
    elif task.task_type == "code_answer":
        starter_code = ""
        if task.options and isinstance(task.options, dict):
            starter_code = task.options.get("starter_code", "")
        await message.answer(
            f"Сложность {task.difficulty}/5\n{task.question_text}\n\n"
            f"Отправь Python-код функции сообщением.\n\n```python\n{starter_code}\n```"
        )
    else:
        await message.answer(
            f"Сложность {task.difficulty}/5\n{task.question_text}\n\nОтветь текстовым сообщением."
        )


@router.callback_query(F.data.startswith("answer:"))
async def answer_callback(callback: CallbackQuery, user_profile, session) -> None:
    _, task_id, answer = callback.data.split(":", 2)
    await _process_answer(
        callback.message, user_profile.id, int(task_id), answer, 0.0, session
    )
    await callback.answer()


@router.message(F.text & ~F.text.in_(MENU_TEXTS))
async def answer_text(message: Message, user_profile, session) -> None:
    redis = None
    async for client in get_redis():
        redis = client
        break
    raw = await redis.get(f"current_task:{user_profile.id}") if redis else None
    if not raw:
        return
    task_id, started = raw.split(":", 1)
    await _process_answer(
        message,
        user_profile.id,
        int(task_id),
        message.text or "",
        max(0.0, time.time() - float(started)),
        session,
    )
    if redis:
        await redis.delete(f"current_task:{user_profile.id}")


async def _process_answer(
    message: Message,
    user_id: int,
    task_id: int,
    answer: str,
    answer_time: float,
    session,
) -> None:
    result = await TaskService(session).answer_task(
        user_id, task_id, answer, answer_time
    )
    await session.commit()
    task = result["task"]
    text = (
        f"Верно! +{result['xp_gained']} XP"
        if result["is_correct"]
        else f"Неверно. Правильный ответ: {task.correct_answer}.\nОбъяснение: {task.explanation}"
    )
    if task.task_type == "code_answer" and not result["is_correct"]:
        text = f"Неверно. {result.get('feedback') or task.explanation}"
    text += f"\nОсвоение темы: {result['mastery'].mastery_level:.0%}. Следующая сложность: {result['mastery'].current_difficulty}/5.\nТекущий уровень: {result['new_level']}."
    await message.answer(text + "\n\nНажми /task для следующего задания.")
