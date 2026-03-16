import datetime
import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Iterable

from app.db.client import DBClient

if TYPE_CHECKING:
    from app.db.models import Product
    from app.db.schemas import ProductFetchResultSchema, UserProductSchema
    from app.parser.uzum import UzumParser
    from app.publisher.publisher import RabbitPublisher


logger = logging.getLogger(__name__)


class ProductService:
    """Сервисный слой для работы с товарами."""

    def __init__(self, parser: "UzumParser", publisher: "RabbitPublisher", check_interval: int) -> None:
        self.parser = parser
        self.publisher = publisher
        self.check_interval = check_interval

    async def add_new_product(self, user_id: int, url: str, number: str, sku_id: str | None) -> None:
        async with DBClient() as db_client:
            product = await db_client.check_and_get_product(number, sku_id)

            if not product:
                product = await db_client.create_and_add_product_to_user(
                    user_id=user_id, url=url, number=number, sku_id=sku_id
                )
                logger.debug("product_id=%s, url=%s created", product.id, url)
                # асинхронно добавим цену и название
                await self.publisher.publish(product.id, url)
                return

            await db_client.add_user_product(user_id, product.id)
            if not product.last_checked_at or product.last_checked_at < self._get_time_to_check(self.check_interval):
                await self.publisher.publish(product.id, url)
                return

    async def get_user_products(self, user_id: int) -> list["Product"]:
        async with DBClient() as db_client:
            return await db_client.get_user_products(user_id)

    async def delete_user_product(self, user_id: int, product_id: int) -> None:
        async with DBClient() as db_client:
            await db_client.delete_user_product(user_id, product_id)

    async def get_product_with_prices(self, product_id: int) -> "Product":
        async with DBClient() as db_client:
            return await db_client.get_product_with_prices(product_id)

    async def get_products_to_check(self):
        async with DBClient() as db_client:
            time_to_check = self._get_time_to_check(self.check_interval)
            products: Iterable["Product"] = await db_client.get_products_to_check(time_to_check)
        return products

    async def get_updated_products(self) -> list["ProductFetchResultSchema"] | None:
        products_to_check = await self.get_products_to_check()
        if not products_to_check:
            return None

        parsed_products = await self.check_updates(products_to_check)
        return self._filter_updated_products(parsed_products)

    async def check_updates(self, products: Iterable["Product"]) -> list["ProductFetchResultSchema"]:
        result: list["ProductFetchResultSchema"] = await self.parser.fetch_products_updates(products)

        async with DBClient() as db_client:
            for parsed_product in result:
                product_data: dict = {
                    "last_checked_at": parsed_product.checked_at,
                }
                if parsed_product.new_price != parsed_product.price:
                    await db_client.add_new_price(parsed_product.id, parsed_product.new_price)
                    product = await db_client.get_product_by_id(parsed_product.id)
                    product_data["last_price"] = parsed_product.new_price
                    if not product.title:
                        product_data["title"] = parsed_product.title

                await db_client.update_product(parsed_product.id, **product_data)
        return result

    async def collect_user_products(self, products: list["ProductFetchResultSchema"]) -> "UserProductSchema":
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

    def _filter_updated_products(self, products: list["ProductFetchResultSchema"]) -> list["ProductFetchResultSchema"]:
        updated_products = []
        for product in products:
            if product.new_price != product.price:
                updated_products.append(product)
        return updated_products

    def _get_time_to_check(self, interval: int) -> datetime.datetime:
        now = datetime.datetime.now(datetime.UTC)
        return now - datetime.timedelta(minutes=interval)
