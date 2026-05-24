import asyncio
import logging

from aiogram import Bot, Dispatcher

from app.bot.handlers import achievements, profile, quests, start, tasks, theory
from app.bot.middlewares.user_middleware import UserMiddleware
from app.core.config import get_settings
from app.core.logging import configure_logging


async def run_bot() -> None:
    configure_logging()
    settings = get_settings()
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is required to run Telegram bot")
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()
    dp.update.middleware(UserMiddleware())
    # Keep the broad "any text answer" task handler last so menu buttons such
    # as "Квесты" and "Теория" are handled by their dedicated routers first.
    for router in [
        start.router,
        profile.router,
        quests.router,
        achievements.router,
        theory.router,
        tasks.router,
    ]:
        dp.include_router(router)
    logging.info("Starting Telegram bot polling")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(run_bot())
