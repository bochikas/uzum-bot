import datetime
import logging
import random
import re
from asyncio import sleep
from typing import Iterable

from playwright.async_api import Page, async_playwright, expect

from app.db.models import Product
from app.db.schemas import ProductFetchResultSchema, ProductMinifiedSchema

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
        await locator.wait_for(state="visible", timeout=10_000)
        price = await locator.inner_text()
        logger.debug("found raw price text: %s", price)
        return price

    async def is_product_unavailable(self, page: Page) -> bool:
        return await page.locator("[data-test-id='empty-results__button']").is_visible()

    async def fetch_product_with_page(self, page: Page, url: str) -> ProductMinifiedSchema:
        logger.debug("parsing product started")
        await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60_000,
        )
        await self.check_captcha(page)
        await page.wait_for_timeout(random.uniform(2_000, 5_000))

        locator = page.get_by_role("button", name="Добавить в корзину")
        await expect(locator).to_be_visible()

        try:  # noqa WPS229
            product_title = await self.parse_product_title(page=page)
            raw_price = await self.parse_product_price(page=page)
            product_price = self._parse_price_to_float(raw_price)
            return ProductMinifiedSchema(title=product_title, price=product_price)
        except Exception:
            logger.exception("error loading %s", url)
            raise
        finally:
            await sleep(random.uniform(1, 4))

    async def check_captcha(self, page: Page) -> None:
        if "/showcaptcha" in page.url:
            raise RuntimeError(f"Uzum CAPTCHA detected: {page.url}")

    async def create_browser(self, p):
        return await p.chromium.launch(
            headless=self.headless,
            args=["--disable-blink-features=AutomationControlled"],
        )

    async def configure_page(self, page: Page) -> None:
        if not self.headless:
            return

        browser = page.context.browser
        if browser is None:
            raise RuntimeError("browser is unavailable for the context")

        chrome_version = browser.version
        major_version = chrome_version.split(".", maxsplit=1)[0]
        current_user_agent = await page.evaluate("navigator.userAgent")
        current_platform = await page.evaluate("navigator.platform")
        user_agent = current_user_agent.replace("HeadlessChrome/", "Chrome/")
        ua_platform = "macOS" if "Mac" in current_platform else "Linux"
        platform_version = "10.15.7" if ua_platform == "macOS" else "6.0.0"
        architecture = "x86" if ua_platform == "macOS" else "x86_64"

        client = await page.context.new_cdp_session(page)
        await client.send(
            "Emulation.setUserAgentOverride",
            {
                "userAgent": user_agent,
                "acceptLanguage": "ru-RU,ru;q=0.9,en;q=0.8",
                "platform": current_platform,
                "userAgentMetadata": {
                    "brands": [
                        {"brand": "Not_A Brand", "version": "99"},
                        {"brand": "Google Chrome", "version": major_version},
                        {"brand": "Chromium", "version": major_version},
                    ],
                    "fullVersionList": [
                        {"brand": "Not_A Brand", "version": "99.0.0.0"},
                        {"brand": "Google Chrome", "version": chrome_version},
                        {"brand": "Chromium", "version": chrome_version},
                    ],
                    "fullVersion": chrome_version,
                    "platform": ua_platform,
                    "platformVersion": platform_version,
                    "architecture": architecture,
                    "model": "",
                    "mobile": False,
                    "bitness": "64",
                    "wow64": False,
                },
            },
        )
        logger.debug("configured headless user agent: %s", user_agent)

    async def fetch_products_updates(self, products: Iterable[Product]) -> list[ProductFetchResultSchema]:
        result: list[ProductFetchResultSchema] = []

        async with async_playwright() as p:
            browser = await self.create_browser(p)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                locale="ru-RU",
                timezone_id="Asia/Tashkent",
            )
            page = await context.new_page()
            await self.configure_page(page)

            try:
                logger.debug("parsing products started")
                for product in products:
                    try:
                        response = await page.goto(product.url, wait_until="load", timeout=60_000)
                        await self.check_captcha(page)

                        logger.debug(
                            "url=%s status=%s final_url=%s",
                            product.url,
                            response.status if response else None,
                            page.url,
                        )

                        await page.wait_for_timeout(3_000)
                        if await self.is_product_unavailable(page=page):
                            continue

                        current_price = await self.parse_product_price(page=page)
                        new_price = self._parse_price_to_float(current_price)
                        parsed_product = ProductFetchResultSchema(
                            id=product.id,
                            price=product.last_price,
                            new_price=new_price,
                            title=product.title,
                            url=product.url,
                            checked_at=datetime.datetime.now(datetime.UTC),
                        )

                        if not product.title:
                            parsed_product.title = await self.parse_product_title(page=page)

                        result.append(parsed_product)

                    except Exception:
                        logger.exception("error loading %s; final_url=%s", product.url, page.url)

                    finally:
                        await sleep(random.uniform(2, 6))

            finally:
                await context.close()
                await browser.close()

        logger.debug("parsing products finished")
        return result

    def _parse_price_to_float(self, price_text: str) -> float:
        digits = re.findall(r"\d+", price_text)
        if not digits:
            raise ValueError(f"cannot parse price from: {price_text!r}")
        return float("".join(digits))
