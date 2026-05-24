from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.core.database import AsyncSessionLocal
from app.services.user_service import UserService


class UserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        telegram_user = data.get("event_from_user")
        async with AsyncSessionLocal() as session:
            data["session"] = session
            if telegram_user:
                user, _ = await UserService(session).get_or_create_from_telegram(
                    telegram_user.id, telegram_user.username, telegram_user.first_name
                )
                data["user_profile"] = user
            result = await handler(event, data)
            await session.commit()
            return result
