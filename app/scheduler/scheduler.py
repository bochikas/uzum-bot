import logging
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from extractor.parser import UzumParser

from db.schemas import UpdatedProductSchema

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

        updated_products = await self.parser.fetch_all_product_updates()
        if not updated_products:
            return
        await self.send_notifications(updated_products)

    async def send_notifications(self, updated_products: dict[int, UpdatedProductSchema]) -> None:
        """Отправка оповещений об изменении цен."""

        if not updated_products:
            return

        await self.bot.send_notification_for_updated_products(updated_products)
