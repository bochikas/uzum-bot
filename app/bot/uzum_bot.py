import logging
import re
from datetime import datetime
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.exc import IntegrityError

from bot.keyboards import KeyBoardButtonType, main_kb
from bot.middlewares import UserIdMiddleware
from config.settings import app_config
from db.client import DBClient, sessionmanager
from scheduler.scheduler import Scheduler

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery, Message

    from db.models import Product
    from db.schemas import UpdatedProduct

logger = logging.getLogger(__name__)


class BroadcastState(StatesGroup):
    """Состояния бота."""

    product_url = State()


class UzumBot:
    def __init__(self):
        self.bot = Bot(token=app_config.telegram.token.get_secret_value())
        self.dp = Dispatcher(storage=MemoryStorage())
        self.router = Router()
        self.register_handlers()
        self.dp.include_router(self.router)
        self.dp.update.outer_middleware(UserIdMiddleware())

        self.scheduler = Scheduler(self)

    def register_handlers(self):
        self.router.message.register(self.handle_start, CommandStart())
        self.router.message.register(self.handle_skip, Command("skip"))
        self.router.message.register(self.add_product, F.text == KeyBoardButtonType.ADD_PRODUCT.value)
        self.router.message.register(self.handle_product_url, BroadcastState.product_url)
        self.router.message.register(self.get_products, F.text == KeyBoardButtonType.PRODUCT_LIST.value)
        self.router.message.register(self.delete_product, F.text == KeyBoardButtonType.DELETE_PRODUCT.value)
        self.router.callback_query.register(self.delete_product_callback, F.data.startswith("delete_"))
        self.router.callback_query.register(self.product_price_history_callback, F.data.startswith("history_"))

    async def on_startup(self, dispatcher):
        sessionmanager.init(app_config.database_uri)
        await self.scheduler.start()

    async def on_shutdown(self, dispatcher):
        await sessionmanager.close()
        await self.scheduler.stop()

    async def run(self):
        self.dp.startup.register(self.on_startup)
        self.dp.shutdown.register(self.on_shutdown)
        await self.dp.start_polling(self.bot)

    async def handle_start(self, message: "Message"):
        """Обработка команды старт."""

        await message.answer("Привет! Выберите действие:", reply_markup=main_kb)

    async def handle_skip(self, message: "Message", state: "FSMContext"):
        await message.answer("Выберите действие", reply_markup=main_kb)
        await state.clear()

    async def add_product(self, message: "Message", state: "FSMContext"):
        """Добавить ссылку на товар."""

        await state.clear()
        await state.set_state(BroadcastState.product_url)
        await message.answer("Введите ссылку")

    async def handle_product_url(self, message: "Message", state: "FSMContext", user_id: int):  # noqa WPS217
        """Обработка сообщения со ссылкой от пользователя."""

        if not message.text or not message.entities:
            return await message.answer(
                "Сообщение не распознано. Пожалуйста, введите ссылку или нажмите /skip для отмены."
            )
        product_url = None
        for entity in message.entities:
            if entity.type == "url":
                product_url = message.text[entity.offset : entity.offset + entity.length]

        if not product_url:
            return await message.answer(
                "Сообщение не распознано. Пожалуйста, введите ссылку или нажмите /skip для отмены."
            )

        parsed_url = urlparse(product_url)
        if parsed_url.hostname != "uzum.uz":
            return await message.answer("Неправильная ссылка")

        captured_value = parse_qs(parsed_url.query)
        # skuid может и не быть
        if sku_id := captured_value.get("skuId"):
            sku_id = sku_id[0]

        pattern = re.compile(r"/product/.*?-([\d\-]+)(?:\?|$)")
        match = pattern.search(parsed_url.path)
        number = match.group(1)

        async with DBClient() as db_client:
            try:
                await db_client.create_and_add_product_to_user(
                    user_id=user_id, url=product_url, number=number, sku_id=sku_id
                )
                await message.answer(f"Добавлена ссылка {product_url}")
            except IntegrityError:
                await message.answer("Вы уже добавляли этот товар")
            finally:
                await state.clear()

    async def get_products(self, message: "Message", user_id: int):
        """Список добавленного товара."""

        if not (products := await self._get_user_products(user_id)):
            await message.answer("У вас нет добавленного товара.")
            return

        builder = InlineKeyboardBuilder()
        for product in products:
            product_title = product.title or product.url
            product_price = product.prices[0].price if product.prices else "?"
            builder.row(
                InlineKeyboardButton(
                    text=f"{product_title[:20]}. Цена: {product_price}. История", callback_data=f"history_{product.id}"
                )
            )
        await message.answer("Ваш список товаров:", reply_markup=builder.as_markup())

    async def product_price_history_callback(self, callback: "CallbackQuery"):
        """Получение истории цен на продукт."""

        product_id = int(callback.data.replace("history_", ""))
        async with DBClient() as db_client:
            product = await db_client.get_product_with_prices(product_id)
        message = f"{product.title}. История цен: "
        for price in product.prices:
            message = f"{message}\n{datetime.strftime(price.created_at, '%d.%m.%Y')} - {price.price}"
        await callback.message.answer(message)

    async def send_notification(self, telegram_id: int, updated_products: list["UpdatedProduct"]) -> None:
        """Отправка оповещения пользователю об изменении цены на товар."""

        builder = InlineKeyboardBuilder()
        for product in updated_products:
            builder.row(
                InlineKeyboardButton(text=f"{product.title[:35]}. Новая цена: {product.price}", url=product.url)
            )
        await self.bot.send_message(telegram_id, "Измененные цены на товары:", reply_markup=builder.as_markup())

    async def delete_product(self, message: "Message", user_id: int):
        """Список товара для удаления."""

        if not (products := await self._get_user_products(user_id)):
            await message.answer("У вас нет добавленного товара.")
            return

        builder = InlineKeyboardBuilder()
        for product in products:
            product_title = product.title or product.url
            product_price = product.prices[0].price if product.prices else "?"
            builder.row(
                InlineKeyboardButton(
                    text=f"{product_title[:35]}. Цена: {product_price}", callback_data=f"delete_{product.id}"
                )
            )
        await message.answer("Ваш список товаров:", reply_markup=builder.as_markup())

    async def delete_product_callback(self, callback: "CallbackQuery", user_id: int):
        """Удаление товара."""

        product_id = int(callback.data.replace("delete_", ""))
        async with DBClient() as db_client:
            await db_client.delete_user_product(user_id, product_id)

        await callback.answer("Товар удален.", show_alert=True)
        await callback.message.delete()

    async def _get_user_products(self, user_id: int) -> list["Product"]:
        async with DBClient() as db_client:
            products = await db_client.get_user_products(user_id)
        return products  # noqa RET504
