from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

def participant_menu_kb():
    """Клавіатура для учасника."""
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(
        KeyboardButton(text="ℹ️ Інформація про сесію"),
        KeyboardButton(text='🚪 Вийти з сесії'),
    )
    return keyboard.as_markup(resize_keyboard=True)