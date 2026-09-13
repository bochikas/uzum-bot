import logging

from app.db.client import DBClient
from app.db.models import User

logger = logging.getLogger(__name__)


class UserService:
    """Сервисный слой для работы с пользователями."""

    async def deactivate_user_by_telegram_id(self, telegram_id: int) -> None:
        async with DBClient() as db:
            await db.update_user_by_telegram_id(telegram_id, active=False)
        logger.info("User telegram_id=%s deactivated", telegram_id)

    async def get_or_activate(self, telegram_id: int, username: str | None) -> User:
        async with DBClient() as db:
            user = await db.get_user_by_telegram_id(telegram_id)

            if user and user.active:
                return user

            if user and not user.active:
                await db.update_user(user.id, active=True, username=username)
                return user

            return await db.create_object(User, telegram_id=telegram_id, username=username)
