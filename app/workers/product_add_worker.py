import asyncio
import json
from logging import config as logging_config
from logging import getLogger

import aio_pika
import aio_pika.abc
from playwright.async_api import Browser, Playwright, async_playwright

from config.logging import LOGGING
from config.settings import app_config
from db.client import DBClient, sessionmanager
from parser.uzum import UzumParser

logging_config.dictConfig(LOGGING)
logger = getLogger(__name__)


class ProductAddWorker:
    connection: aio_pika.abc.AbstractRobustConnection | None = None
    channel: aio_pika.abc.AbstractChannel
    exchange: aio_pika.abc.AbstractExchange
    queue: aio_pika.abc.AbstractQueue
    playwright: Playwright | None = None
    browser: Browser | None = None
    parser: UzumParser

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

    async def start(self):
        sessionmanager.init(app_config.database_uri)
        self.connection = await aio_pika.connect_robust(app_config.rabbitmq.rabbitmq_uri)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=1)
        self.exchange = await self.channel.declare_exchange(
            app_config.rabbitmq.exchange, type=app_config.rabbitmq.exchange_type, durable=True
        )
        self.queue = await self.channel.declare_queue(app_config.rabbitmq.queue_product_add, durable=True)
        await self.queue.bind(self.exchange, routing_key=app_config.rabbitmq.routing_key_product_add)

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            args=["--start-maximized", "--disable-blink-features=AutomationControlled"],
            headless=app_config.parser.headless_mode,
        )

        self.parser = UzumParser(headless=app_config.parser.headless_mode)

    async def run(self):
        async with self.queue.iterator() as queue_iter:
            async for message in queue_iter:
                await self.handle_message(message)

    async def handle_message(self, message: aio_pika.IncomingMessage):
        url = None
        try:
            payload = json.loads(message.body.decode())
            product_id = payload.get("product_id")
            url = payload.get("url")
            if not product_id or not url:
                logger.error("invalid payload: %s", payload)
                await message.ack()
                return

            logger.info("product_id=%s, url=%s", product_id, url)

            context = await self.browser.new_context(no_viewport=True)
            page = await context.new_page()
            try:
                parsed_product = await self.parser.fetch_product_with_page(page, url)
            finally:
                await context.close()

            async with DBClient() as db_client:
                await db_client.update_product(product_id, **parsed_product.model_dump())
                await db_client.add_new_price(product_id, parsed_product.price)

            await message.ack()
        except json.JSONDecodeError:
            logger.exception("error decoding json: %s", message.body)
            await message.ack()
        except Exception:
            await message.nack(requeue=True)
            logger.exception("error loading %s", url)

    async def stop(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        if self.connection:
            await self.connection.close()
        await sessionmanager.close()


async def main():
    async with ProductAddWorker() as worker:
        await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
