import logging
from datetime import datetime
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from db.schemas import UpdatedProductSchema

if TYPE_CHECKING:
    from bot.uzum_bot import UzumBot
    from services.product import ProductService

logger = logging.getLogger(__name__)


class Scheduler:
    """Планировщик задач."""

    scheduler: AsyncIOScheduler

    def __init__(
        self, bot: "UzumBot", service: "ProductService", run_interval: int, run_on_startup: bool = False
    ) -> None:
        self.scheduler = AsyncIOScheduler()
        self.service = service
        self.bot = bot
        self.run_interval = run_interval
        self.run_on_startup = run_on_startup
        self.add_all_jobs()

    def add_all_jobs(self) -> None:
        next_run = datetime.now() if self.run_on_startup else None
        self.scheduler.add_job(self.update_all_products, "interval", hours=self.run_interval, next_run_time=next_run)

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
