import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Iterable

from db.client import DBClient
from db.models import Product
from db.schemas import UpdatedProductSchema, UserProductSchema

if TYPE_CHECKING:
    from publisher.publisher import RabbitPublisher

    from parser.uzum import UzumParser


logger = logging.getLogger(__name__)


class ProductService:
    """Сервисный слой для работы с товарами."""

    def __init__(self, parser: "UzumParser", publisher: "RabbitPublisher") -> None:
        self.parser = parser
        self.publisher = publisher

    async def add_new_product(self, user_id: int, url: str, number: str, sku_id: str | None) -> None:
        async with DBClient() as db_client:
            product_id = await db_client.create_and_add_product_to_user(
                user_id=user_id, url=url, number=number, sku_id=sku_id
            )
            logger.debug("product_id=%s, url=%s created", product_id, url)
            # асинхронно добавим цену и название
        await self.publisher.publish(product_id, url)

    async def get_user_products(self, user_id: int) -> list["Product"]:
        async with DBClient() as db_client:
            return await db_client.get_user_products(user_id)

    async def delete_user_product(self, user_id: int, product_id: int) -> None:
        async with DBClient() as db_client:
            await db_client.delete_user_product(user_id, product_id)

    async def get_product_with_prices(self, product_id: int) -> Product:
        async with DBClient() as db_client:
            return await db_client.get_product_with_prices(product_id)

    async def check_updates(self) -> list[UpdatedProductSchema]:
        updated: list[UpdatedProductSchema] = []

        async with DBClient() as db_client:
            products: Iterable[Product] = await db_client.get_model_objects(Product)

        if not products:
            return updated

        updated: list[UpdatedProductSchema] = await self.parser.fetch_products_update(products)

        async with DBClient() as db_client:
            for updated_product in updated:
                await db_client.add_new_price(updated_product.id, updated_product.new_price)
                product = await db_client.get_product_by_id(updated_product.id)
                if not product.title:
                    await db_client.update_product(updated_product.id, title=updated_product.title)

        return updated

    async def collect_user_products(self, products: list[UpdatedProductSchema]) -> UserProductSchema:
        products_by_id = {product.id: product for product in products}
        async with DBClient() as db_client:
            users = await db_client.get_users_by_product_ids(products_by_id.keys())
            all_user_products = await db_client.get_all_user_products()

        user_updated_products_temp = defaultdict(list)
        for obj in all_user_products:
            if products_by_id.get(obj.product_id):
                user_updated_products_temp[obj.user_id].append(products_by_id[obj.product_id])

        user_updated_products = defaultdict(list)
        for user in users:
            user_updated_products[user.telegram_id] = user_updated_products_temp[user.id]
        return user_updated_products
