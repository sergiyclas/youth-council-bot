from aiogram import types, Dispatcher
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

async def start_command(message: types.Message):
    # Правильне створення клавіатури
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Створити сесію")],
            [KeyboardButton(text="Приєднатися до сесії")]
        ],
        resize_keyboard=True
    )
    await message.answer(
        "Привіт! Ви можете:\n"
        "- Створити сесію\n"
        "- Приєднатися до сесії\n"
        "Виберіть дію нижче.",
        reply_markup=keyboard
    )

def register_common_handlers(dp: Dispatcher):
    dp.message.register(start_command, Command("start"))
