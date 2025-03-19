import logging
import re
from urllib.parse import urlparse
from urllib.parse import parse_qs

from aiogram import Bot, F, types, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import exc

from db.client import DBClient
from db.models import Product, User
from bot.schemas import KeyBoardButtonType
from config.settings import app_config

logger = logging.getLogger(__name__)


main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=KeyBoardButtonType.ADD_PRODUCT.value)],
        [KeyboardButton(text=KeyBoardButtonType.DELETE_PRODUCT.value)],
        [KeyboardButton(text=KeyBoardButtonType.PRODUCT_LIST.value)],
    ],
    resize_keyboard=True,
)

dp = Dispatcher(storage=MemoryStorage())
bot = Bot(token=app_config.telegram.token.get_secret_value())


class BroadcastState(StatesGroup):
    """Состояния бота."""

    product_url = State()


@dp.message(CommandStart())
async def start(message: Message):
    """Обработка команды старт."""

    async with DBClient() as db_client:
        user = await db_client.get_user_by_telegram_id(message.from_user.id)
        if not user:
            await db_client.create_object(User, telegram_id=message.from_user.id)
    await message.answer("Привет! Выберите действие:", reply_markup=main_kb)


@dp.message(Command("skip"))
async def skip(message: Message, state: FSMContext):
    await message.answer("Выберите действие", reply_markup=main_kb)
    await state.clear()


@dp.message(F.text == KeyBoardButtonType.ADD_PRODUCT.value)
async def add_product(message: Message, state: FSMContext):
    """Добавить ссылку на товар."""

    await state.clear()
    await state.set_state(BroadcastState.product_url)
    await message.answer("Введите ссылку")


@dp.message(BroadcastState.product_url)
async def handle_product_url(message: Message, state: FSMContext):
    """Обработка сообщения со ссылкой от пользователя."""

    if not message.text or not message.entities:
        return await message.answer("Сообщение не распознано. Пожалуйста, введите ссылку или нажмите /skip для отмены.")
    product_url = None
    for entity in message.entities:
        if entity.type == "url":
            product_url = message.text[entity.offset : entity.offset + entity.length]

    if not product_url:
        return await message.answer("Сообщение не распознано. Пожалуйста, введите ссылку или нажмите /skip для отмены.")

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
        if not user.active:
            await db_client.update_object(User, user, active=True)
        try:
            await db_client.create_object(Product, user_id=user.id, url=product_url, number=number, sku_id=sku_id)
            await message.answer(f"Добавлена ссылка {product_url}")
        except exc.IntegrityError:
            await message.answer("Вы уже добавляли этот товар")
        finally:
            await state.clear()


@dp.message(F.text == KeyBoardButtonType.PRODUCT_LIST.value)
async def get_products(message: Message):
    """Список добавленного товара."""

    async with DBClient() as db_client:
        user: User = await db_client.get_user_by_telegram_id(message.from_user.id)
        products: list[Product] = await db_client.get_products_by_user_id(user.id)

    if not products:
        await message.answer("У вас нет добавленного товара.")
        return

    builder = InlineKeyboardBuilder()
    for product in products:
        product_title = product.title or product.url
        title = f"{product_title[:40]}. Цена: {product.price or "?"} сум"
        builder.row(types.InlineKeyboardButton(text=title, url=product.url))

    await message.answer("Ваш список товаров:", reply_markup=builder.as_markup())


@dp.message(F.text == KeyBoardButtonType.DELETE_PRODUCT.value)
async def delete_product(message: Message):
    """Удаление товара."""

    async with DBClient() as db_client:
        user: User = await db_client.get_user_by_telegram_id(message.from_user.id)
        products: list[Product] = await db_client.get_products_by_user_id(user.id)

    if not products:
        await message.answer("У вас нет добавленного товара.")
        return

    builder = InlineKeyboardBuilder()
    for product in products:
        product_title = product.title or product.url
        title = f"{product_title[:40]}. Цена: {product.price or "?"} сум"
        builder.button(text=title, callback_data=f"delete_{product.id}")
    builder.adjust(1)

    await message.answer("Ваш список товаров:", reply_markup=builder.as_markup())
