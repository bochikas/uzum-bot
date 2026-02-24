from collections import defaultdict
from typing import TYPE_CHECKING, Iterable, Type

from config.settings import app_config
from db.client import DBClient
from db.models import Product
from db.schemas import UpdatedProductSchema, UserProductSchema

if TYPE_CHECKING:
    from parser.uzum import UzumParser


class ProductService:
    def __init__(self, parser: Type["UzumParser"]) -> None:
        self.parser = parser(headless=app_config.headless_mode)

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
