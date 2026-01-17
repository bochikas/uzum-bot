import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from extractor.parser import UzumParser

from db.client import DBClient
from db.schemas import UpdatedProduct

if TYPE_CHECKING:
    from bot.uzum_bot import UzumBot

logger = logging.getLogger(__name__)


class Scheduler:
    """Планировщик задач."""

    scheduler: AsyncIOScheduler

    def __init__(self, bot: "UzumBot") -> None:
        self.scheduler = AsyncIOScheduler()
        self.parser = UzumParser()
        self.bot = bot
        self.add_all_jobs()

    def add_all_jobs(self) -> None:
        self.scheduler.add_job(self.update_all_products, "interval", hours=24)

    async def start(self) -> None:
        """Start."""

        self.scheduler.start()

    async def stop(self) -> None:
        """Stop."""

        self.scheduler.shutdown()

    async def update_all_products(self) -> None:
        """Парсинг цены и заголовка товаров."""

        updated_products = await self.parser.update_all_products()
        if not updated_products:
            return
        await self.send_notifications(updated_products)

    async def send_notifications(self, updated_products: dict[int, UpdatedProduct]) -> None:
        """Отправка оповещений об изменении цен."""

        if not updated_products:
            return

        async with DBClient() as db_client:
            users = await db_client.get_users_by_product_ids(updated_products.keys())
            user_updated_products = defaultdict(list)
            for obj in await db_client.get_all_user_products():
                if updated_products.get(obj.product_id):
                    user_updated_products[obj.user_id].append(updated_products[obj.product_id])

        for user in users:
            await self.bot.send_notification(user.telegram_id, user_updated_products[user.id])
