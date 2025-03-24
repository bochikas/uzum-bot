from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from db.client import DBClient
from db.models import User


class UserIdMiddleware(BaseMiddleware):
    """Middleware для добавления ID пользователя из БД."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data["event_from_user"]
        data["user_id"] = await self._get_user_id(user.id, user.username)
        return await handler(event, data)

    async def _get_user_id(self, user_id: int, username: str | None = None) -> int:
        async with DBClient() as db_client:
            user = await db_client.get_user_by_telegram_id(user_id)
            if not user:
                user = await db_client.create_object(User, telegram_id=user.id, username=username)
        return user.id
