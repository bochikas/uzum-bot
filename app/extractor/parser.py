import logging
import random
import re
from asyncio import sleep

from playwright.async_api import Page, async_playwright, expect

from db.client import DBClient
from db.models import Product
from db.schemas import UpdatedProduct

logger = logging.getLogger(__name__)


class UzumParser:
    async def fetch_product_title(self, page: Page) -> str:
        locator = page.locator("[data-test-id='text__product-name']")
        await expect(locator).to_have_text(re.compile(r".+"), timeout=10_000)
        title = await locator.inner_text()
        logger.debug("found product title: %s", title)
        return title

    async def fetch_product_price(self, page: Page) -> str:
        locator = page.locator("[data-test-id='text__product-price']")
        await expect(locator).to_have_text(re.compile(r".+"), timeout=10_000)
        price = await locator.inner_text()
        logger.debug("found raw price text: %s", price)
        return price

    def _parse_price_to_float(self, price_text: str) -> float:
        digits = re.findall(r"\d+", price_text)
        if not digits:
            raise ValueError(f"cannot parse price from: {price_text!r}")
        return float("".join(digits))

    async def update_all_products(self) -> dict[int, UpdatedProduct]:
        updated_products: dict[int, UpdatedProduct] = {}

        async with DBClient() as db_client:
            products: list[Product] = await db_client.get_model_objects(Product)
            if not products:
                return updated_products

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=False, args=["--start-maximized", "--disable-blink-features=AutomationControlled"]
                )
                context = await browser.new_context(no_viewport=True)
                page = await context.new_page()
                try:
                    logger.info("parsing products started")
                    for product in products:
                        await page.goto(product.url, wait_until="domcontentloaded")
                        await page.wait_for_timeout(random.uniform(1000, 2000))

                        try:  # noqa WPS229
                            if not product.title:
                                product.title = await self.fetch_product_title(page=page)

                            current_price = await self.fetch_product_price(page=page)
                            new_price = self._parse_price_to_float(current_price)
                            product_price = product.prices[0].price if product.prices else None
                            if not product_price or new_price != product_price:
                                updated_products[product.id] = UpdatedProduct(
                                    id=product.id, price=new_price, title=product.title, url=product.url
                                )

                                await db_client.add_new_price(product.id, new_price)
                        except Exception:
                            logger.exception("error loading %s", product.url)
                        finally:
                            await sleep(random.uniform(1, 4))
                finally:
                    await context.close()
                    await browser.close()

            await db_client.db_session.commit()
            logger.info("parsing products finished")
        return updated_products
