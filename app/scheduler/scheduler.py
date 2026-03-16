import datetime
import logging
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler

if TYPE_CHECKING:
    from app.bot.uzum_bot import UzumBot
    from app.db.schemas import ProductFetchResultSchema
    from app.services.product import ProductService

logger = logging.getLogger(__name__)


class ProductScheduler:
    """Планировщик задач."""

    scheduler: AsyncIOScheduler

    def __init__(self, bot: "UzumBot", service: "ProductService", run_interval: int) -> None:
        self.scheduler = AsyncIOScheduler()
        self.service = service
        self.bot = bot
        self.run_interval = run_interval
        self.add_all_jobs()

    def add_all_jobs(self) -> None:
        self.scheduler.add_job(
            self.update_all_products, "interval", minutes=self.run_interval, next_run_time=datetime.datetime.now()
        )

    async def start(self) -> None:
        """Start."""

        self.scheduler.start()

    async def stop(self) -> None:
        """Stop."""

        self.scheduler.shutdown()

    async def update_all_products(self) -> None:
        """Парсинг цены и заголовка товаров."""

        updated_products = await self.service.get_updated_products()
        if not updated_products:
            return
        await self.send_notifications(updated_products)

    async def send_notifications(self, updated_products: list["ProductFetchResultSchema"]) -> None:
        """Отправка оповещений об изменении цен."""

        user_products = await self.service.collect_user_products(updated_products)
        await self.bot.send_notification_for_updated_products(user_products)
