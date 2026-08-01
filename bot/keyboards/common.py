from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def common_kb():
    """Клавіатура для загальних дій."""
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(
        KeyboardButton(text="Створити сесію"),
        KeyboardButton(text="Приєднатися до сесії"),
        KeyboardButton(text="📋 Допомога"),
    )
    return keyboard.adjust(1).as_markup(resize_keyboard=True)


def vote_kb():
    """Клавіатура для голосування."""
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(
        KeyboardButton(text="За"),
        KeyboardButton(text="Проти"),
        KeyboardButton(text="Утримаюсь")
    )
    return keyboard.adjust(1).as_markup(resize_keyboard=True)

def pdf_kb():
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(
        KeyboardButton(text="Об'єднати PDF"),
        # KeyboardButton(text="Завершити об'єднання"),
    )
    return keyboard.adjust(1).as_markup(resize_keyboard=True)