from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.services.user import UserService


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
        user_service = UserService()
        user = await user_service.get_or_activate(user_id, username)
        return user.id
