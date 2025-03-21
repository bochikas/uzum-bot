import logging
import random
from asyncio import sleep

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
from seleniumbase import Driver

from db.client import DBClient
from db.models import Product

logger = logging.getLogger(__name__)


async def fetch_product_prices() -> None:
    """Парсинг цены и заголовка товаров."""

    driver = Driver(uc=True, headless=True)
    async with DBClient() as db_client:
        products: list[Product] = await db_client.get_model_objects(Product)
        logger.info("parsing products started")
        for product in products:
            driver.get(product.url)

            try:  # noqa WPS229
                price_element = WebDriverWait(driver, 3).until(
                    expected_conditions.presence_of_element_located(
                        (By.CSS_SELECTOR, 'span[data-test-id="text__product-price"]')
                    )
                )
                current_price = price_element.text
                logger.debug(f"found price: {current_price}")
                current_price = float(current_price.replace(" ", "", 1).split()[0])
                product_price = product.prices[0].price if product.prices else None
                if not product_price or current_price != product_price:
                    await db_client.add_new_price(product.id, current_price)
                if not product.title:
                    title_element = WebDriverWait(driver, 2).until(
                        expected_conditions.presence_of_element_located(
                            (By.CSS_SELECTOR, 'h1[data-test-id="text__product-name"]')
                        )
                    )
                    product.title = title_element.text
                    logger.debug(f"found product title: {product.title}")
            except Exception:
                logger.exception("error loading %s", product.url)
                product.price = product.price or None
            finally:
                await sleep(random.uniform(1, 4))
        await db_client.db_session.commit()
        logger.info("parsing products finished")
