from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def admin_keyboard():
    # Клавіатура для адміністратора
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Змінити порядок денний")],
            [KeyboardButton(text="Почати голосування")],
            [KeyboardButton(text="Завершити сесію")]
        ],
        resize_keyboard=True
    )

def voting_keyboard():
    # Клавіатура для голосування
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="За")],
            [KeyboardButton(text="Проти")],
            [KeyboardButton(text="Утримався")]
        ],
        resize_keyboard=True
    )
