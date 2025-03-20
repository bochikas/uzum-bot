from enum import Enum

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


class KeyBoardButtonType(Enum):
    ADD_PRODUCT = "Добавить ссылку на товар"
    DELETE_PRODUCT = "Удалить товар из списка"
    PRODUCT_LIST = "Список добавленного товара"


main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=KeyBoardButtonType.ADD_PRODUCT.value)],
        [KeyboardButton(text=KeyBoardButtonType.PRODUCT_LIST.value)],
        [KeyboardButton(text=KeyBoardButtonType.DELETE_PRODUCT.value)],
    ],
    resize_keyboard=True,
)
