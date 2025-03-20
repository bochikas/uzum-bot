import logging
import re
from urllib.parse import parse_qs, urlparse

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import exc

from bot.keyboards import KeyBoardButtonType, main_kb
from config.settings import app_config
from db.client import DBClient, sessionmanager
from db.models import Product, User

logger = logging.getLogger(__name__)


class BroadcastState(StatesGroup):
    """Состояния бота."""

    product_url = State()


class UzumBot:
    def __init__(self, scheduler=None):
        self.bot = Bot(token=app_config.telegram.token.get_secret_value())
        self.dp = Dispatcher(storage=MemoryStorage())
        self.router = Router()
        self.register_handlers()
        self.dp.include_router(self.router)
        if scheduler:
            self.scheduler = scheduler()

    def register_handlers(self):
        self.router.message.register(self.handle_start, CommandStart())
        self.router.message.register(self.handle_skip, Command("skip"))
        self.router.message.register(self.add_product, F.text == KeyBoardButtonType.ADD_PRODUCT.value)
        self.router.message.register(self.handle_product_url, BroadcastState.product_url)
        self.router.message.register(self.get_products, F.text == KeyBoardButtonType.PRODUCT_LIST.value)
        self.router.message.register(self.delete_product, F.text == KeyBoardButtonType.DELETE_PRODUCT.value)
        self.router.callback_query.register(self.delete_product_callback)

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

    async def handle_start(self, message: Message):
        """Обработка команды старт."""

        async with DBClient() as db_client:
            user = await db_client.get_user_by_telegram_id(message.from_user.id)
            if not user:
                await db_client.create_object(
                    User, telegram_id=message.from_user.id, username=message.from_user.username
                )
        await message.answer("Привет! Выберите действие:", reply_markup=main_kb)

    async def handle_skip(self, message: Message, state: FSMContext):
        await message.answer("Выберите действие", reply_markup=main_kb)
        await state.clear()

    async def add_product(self, message: Message, state: FSMContext):
        """Добавить ссылку на товар."""

        await state.clear()
        await state.set_state(BroadcastState.product_url)
        await message.answer("Введите ссылку")

    async def handle_product_url(self, message: Message, state: FSMContext):  # noqa WPS217
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
        captured_value = parse_qs(parsed_url.query)
        # skuid может и не быть
        if sku_id := captured_value.get("skuId"):
            sku_id = sku_id[0]

        pattern = re.compile(r"/product/.*?-([\d\-]+)(?:\?|$)")
        match = pattern.search(parsed_url.path)
        number = match.group(1)

        async with DBClient() as db_client:
            user = await db_client.get_user_by_telegram_id(message.from_user.id)
            try:
                await db_client.create_and_add_product_to_user(
                    user_id=user.id, url=product_url, number=number, sku_id=sku_id
                )
                await message.answer(f"Добавлена ссылка {product_url}")
            except exc.IntegrityError:
                await message.answer("Вы уже добавляли этот товар")
            finally:
                await state.clear()

    async def get_products(self, message: Message):
        """Список добавленного товара."""

        if not (products := await self._get_user_products(message.from_user.id)):
            await message.answer("У вас нет добавленного товара.")
            return

        builder = InlineKeyboardBuilder()
        for product in products:
            product_title = product.title or product.url
            product_price = product.prices[0].price if product.prices else "?"
            builder.row(InlineKeyboardButton(text=f"{product_title[:35]}. Цена: {product_price}", url=product.url))

        await message.answer("Ваш список товаров:", reply_markup=builder.as_markup())

    async def delete_product(self, message: Message):
        """Удаление товара."""

        if not (products := await self._get_user_products(message.from_user.id)):
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

    async def delete_product_callback(self, callback: CallbackQuery):
        product_id = int(callback.data.replace("delete_", ""))
        async with DBClient() as db_client:
            user: User = await db_client.get_user_by_telegram_id(callback.from_user.id)
            await db_client.delete_user_product(user.id, product_id)

        await callback.answer("Товар удален.", show_alert=True)
        await callback.message.delete()

    async def _get_user_products(self, telegram_id: int) -> list[Product]:
        async with DBClient() as db_client:
            user: User = await db_client.get_user_by_telegram_id(telegram_id)
            products = await db_client.get_user_products(user.id)
        return products  # noqa RET504
