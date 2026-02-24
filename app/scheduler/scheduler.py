import logging
from datetime import datetime
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from db.schemas import UpdatedProductSchema
from parser.uzum import UzumParser
from services.product import ProductService

if TYPE_CHECKING:
    from bot.uzum_bot import UzumBot

logger = logging.getLogger(__name__)


class Scheduler:
    """Планировщик задач."""

    scheduler: AsyncIOScheduler

    def __init__(self, bot: "UzumBot") -> None:
        self.scheduler = AsyncIOScheduler()
        self.service = ProductService(parser=UzumParser)
        self.bot = bot
        self.add_all_jobs()

    def add_all_jobs(self) -> None:
        self.scheduler.add_job(self.update_all_products, "interval", hours=24, next_run_time=datetime.now())

    async def start(self) -> None:
        """Start."""

        self.scheduler.start()

    async def stop(self) -> None:
        """Stop."""

        self.scheduler.shutdown()

    async def update_all_products(self) -> None:
        """Парсинг цены и заголовка товаров."""

        updated_products = await self.service.check_updates()
        if not updated_products:
            return
        await self.send_notifications(updated_products)

    async def send_notifications(self, updated_products: list[UpdatedProductSchema]) -> None:
        """Отправка оповещений об изменении цен."""

        user_products = await self.service.collect_user_products(updated_products)
        await self.bot.send_notification_for_updated_products(user_products)
