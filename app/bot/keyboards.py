from enum import Enum

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


class KeyBoardButtonType(Enum):
    ADD_PRODUCT = "Добавить товар"
    DELETE_PRODUCT = "Удалить товар"
    PRODUCT_LIST = "Добавленные"


main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=KeyBoardButtonType.ADD_PRODUCT.value)],
        [KeyboardButton(text=KeyBoardButtonType.DELETE_PRODUCT.value)],
        [KeyboardButton(text=KeyBoardButtonType.PRODUCT_LIST.value)],
    ],
    resize_keyboard=True,
)
