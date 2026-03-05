import json

import aio_pika
import aio_pika.abc

from config.settings import app_config


class RabbitPublisher:
    connection: aio_pika.abc.AbstractRobustConnection
    channel: aio_pika.abc.AbstractChannel
    exchange: aio_pika.abc.AbstractExchange

    async def start(self):
        self.connection = await aio_pika.connect_robust(app_config.rabbitmq.rabbitmq_uri)
        self.channel = await self.connection.channel()
        self.exchange = await self.channel.declare_exchange(
            app_config.rabbitmq.exchange, type=app_config.rabbitmq.exchange_type, durable=True
        )

    async def publish(self, product_id: int, url: str):
        payload = json.dumps({"product_id": product_id, "url": url}).encode()

        await self.exchange.publish(
            aio_pika.Message(
                body=payload, delivery_mode=aio_pika.DeliveryMode.PERSISTENT, content_type="application/json"
            ),
            routing_key=app_config.rabbitmq.routing_key_product_add,
        )

    async def close(self):
        await self.channel.close()
        await self.connection.close()
