import logging
import random
import re
from asyncio import sleep
from typing import Iterable

from playwright.async_api import Page, async_playwright, expect

from db.models import Product
from db.schemas import ProductMinifiedSchema, UpdatedProductSchema

logger = logging.getLogger(__name__)


class UzumParser:
    """Парсер Узум."""

    def __init__(self, headless: bool = True):
        self.headless = headless

    async def parse_product_title(self, page: Page) -> str:
        locator = page.locator("[data-test-id='text__product-name']")
        await expect(locator).to_have_text(re.compile(r".+"), timeout=10_000)
        title = await locator.inner_text()
        logger.debug("found product title: %s", title)
        return title

    async def parse_product_price(self, page: Page) -> str:
        locator = page.locator("[data-test-id='text__product-price']")
        await expect(locator).to_have_text(re.compile(r".+"), timeout=10_000)
        price = await locator.inner_text()
        logger.debug("found raw price text: %s", price)
        return price

    async def fetch_product(self, url: str) -> ProductMinifiedSchema:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                args=["--start-maximized", "--disable-blink-features=AutomationControlled"], headless=self.headless
            )
            context = await browser.new_context(no_viewport=True)
            page = await context.new_page()
            try:
                logger.debug("parsing single product started")
                await page.goto(url, wait_until="load")
                await page.wait_for_timeout(random.uniform(2000, 5000))
                locator = page.get_by_role("button", name="Добавить в корзину")
                await expect(locator).to_be_visible()

                try:  # noqa WPS229
                    product_title = await self.parse_product_title(page=page)
                    raw_price = await self.parse_product_price(page=page)
                    product_price = self._parse_price_to_float(raw_price)
                except Exception:
                    logger.exception("error loading %s", url)
                finally:
                    await sleep(random.uniform(1, 4))
            finally:
                await context.close()
                await browser.close()
        return ProductMinifiedSchema(title=product_title, price=product_price)

    async def fetch_products_update(self, products: Iterable[Product]) -> list[UpdatedProductSchema]:
        updated_products: list[UpdatedProductSchema] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                args=["--start-maximized", "--disable-blink-features=AutomationControlled"], headless=self.headless
            )
            context = await browser.new_context(no_viewport=True)
            page = await context.new_page()
            try:
                logger.debug("parsing products started")
                for product in products:
                    await page.goto(product.url, wait_until="load")
                    await page.wait_for_timeout(random.uniform(1000, 2000))

                    try:  # noqa WPS229
                        current_price = await self.parse_product_price(page=page)
                        new_price = self._parse_price_to_float(current_price)
                        product_price = product.prices[0].price if product.prices else None
                        if not product_price or new_price != product_price:
                            updated_product = UpdatedProductSchema(
                                id=product.id,
                                price=product_price,
                                new_price=new_price,
                                title=product.title,
                                url=product.url,
                            )
                            if not product.title:
                                updated_product.title = await self.parse_product_title(page=page)
                            updated_products.append(updated_product)

                    except Exception:
                        logger.exception("error loading %s", product.url)
                    finally:
                        await sleep(random.uniform(1, 4))
            finally:
                await context.close()
                await browser.close()

        logger.debug("parsing products finished")
        return updated_products

    def _parse_price_to_float(self, price_text: str) -> float:
        digits = re.findall(r"\d+", price_text)
        if not digits:
            raise ValueError(f"cannot parse price from: {price_text!r}")
        return float("".join(digits))
