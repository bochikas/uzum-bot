import logging
import random
from asyncio import sleep
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from black.trans import defaultdict
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
from seleniumbase import Driver

from db.client import DBClient
from db.models import Product
from db.schemas import UpdatedProduct

if TYPE_CHECKING:
    from bot.uzum_bot import UzumBot

logger = logging.getLogger(__name__)


class Scheduler:
    """Планировщик задач."""

    scheduler: AsyncIOScheduler

    def __init__(self, bot: "UzumBot") -> None:
        self.scheduler = AsyncIOScheduler()
        self.bot = bot
        self.add_all_jobs()

    def add_all_jobs(self) -> None:
        self.scheduler.add_job(self.fetch_product_prices, "interval", hour="24")

    async def start(self) -> None:
        """Start."""

        self.scheduler.start()

    async def stop(self) -> None:
        """Stop."""

        self.scheduler.shutdown()

    async def fetch_product_prices(self) -> None:
        """Парсинг цены и заголовка товаров."""

        updated_products = {}
        driver = Driver(uc=True, headless=True)
        async with DBClient() as db_client:
            products: list[Product] = await db_client.get_model_objects(Product)
            logger.info("parsing products started")
            for product in products:
                driver.get(product.url)

                try:  # noqa WPS229
                    if not product.title:
                        title_element = WebDriverWait(driver, 3).until(
                            expected_conditions.presence_of_element_located(
                                (By.CSS_SELECTOR, 'h1[data-test-id="text__product-name"]')
                            )
                        )
                        product.title = title_element.text
                        logger.debug(f"found product title: {product.title}")

                    price_element = WebDriverWait(driver, 2).until(
                        expected_conditions.presence_of_element_located(
                            (By.CSS_SELECTOR, 'span[data-test-id="text__product-price"]')
                        )
                    )
                    current_price = price_element.text
                    logger.debug(f"found price: {current_price}")
                    new_price = float(current_price.replace(" ", "", 1).split()[0])
                    product_price = product.prices[0].price if product.prices else None
                    if not product_price or new_price != product_price:
                        updated_products[product.id] = UpdatedProduct(
                            id=product.id, price=new_price, title=product.title, url=product.url
                        )

                        await db_client.add_new_price(product.id, new_price)
                except Exception:
                    logger.exception("error loading %s", product.url)
                    product.price = product.price or None
                finally:
                    await sleep(random.uniform(1, 4))
            await db_client.db_session.commit()
            logger.info("parsing products finished")
        await self.send_notifications(updated_products)

    async def send_notifications(self, updated_products: dict[int, UpdatedProduct]) -> None:
        """Отправка оповещений об изменении цен."""

        async with DBClient() as db_client:
            users = await db_client.get_users_by_product_ids(updated_products.keys())
            user_updated_products = defaultdict(list)
            for obj in await db_client.get_all_user_products():
                if updated_products.get(obj.product_id):
                    user_updated_products[obj.user_id].append(updated_products[obj.product_id])

        for user in users:
            await self.bot.send_notification(user.telegram_id, user_updated_products[user.id])
