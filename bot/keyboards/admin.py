from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

def admin_menu_kb():
    """Клавіатура для вибору дій адміністратором."""
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(
        KeyboardButton(text="Створити сесію"),
        KeyboardButton(text="Приєднатися до сесії")
    )
    return keyboard.adjust(2).as_markup(resize_keyboard=True)

def session_control_kb():
    """Клавіатура для керування сесією."""
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(
        KeyboardButton(text="🔄 Змінити порядок денний"),
        KeyboardButton(text="✅ Почати голосування по питаннях плану"),
        KeyboardButton(text="❌ Завершити сесію")
    )
    return keyboard.adjust(1).as_markup(resize_keyboard=True)

def vote_kb():
    """Клавіатура для голосування."""
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(
        KeyboardButton(text="За"),
        KeyboardButton(text="Проти"),
        KeyboardButton(text="Утримався")
    )
    return keyboard.adjust(1).as_markup(resize_keyboard=True)

def force_end_vote_kb():
    """Клавіатура для примусового завершення голосування."""
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(
        KeyboardButton(text="Завершити опитування по поточному питанню")
    )
    return keyboard.as_markup(resize_keyboard=True)


def admin_vote_kb():
    """Клавіатура для управління після голосування."""
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(
        KeyboardButton(text="Голосувати за наступне питання"),
        KeyboardButton(text="❌ Завершити сесію")
    )
    return keyboard.adjust(1).as_markup(resize_keyboard=True)

def back_kb():
    """Клавіатура з кнопкою назад."""
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text="Назад"))
    return keyboard.as_markup(resize_keyboard=True)