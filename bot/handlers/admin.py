from aiogram import types, Dispatcher
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from bot.keyboards.admin import admin_keyboard, voting_keyboard
import random

class AdminState(StatesGroup):
    session_name = State()
    session_password = State()
    agenda = State()

async def create_session(message: types.Message, state: FSMContext):
    if message.text == "Створити сесію":
        await message.answer("Введіть назву сесії:")
        await state.set_state(AdminState.session_name)

async def set_session_name(message: types.Message, state: FSMContext, db):
    session_name = message.text
    await state.update_data(session_name=session_name)
    await message.answer("Введіть пароль для сесії:")
    await state.set_state(AdminState.session_password)

async def set_session_password(message: types.Message, state: FSMContext, db):
    session_password = message.text
    session_data = await state.get_data()
    session_name = session_data["session_name"]
    session_code = random.randint(100000, 999999)

    db.create_session(session_code, session_name, session_password, message.from_user.id)
    await message.answer(
        f"Сесія створена!\nКод сесії: {session_code}\nПароль: {session_password}\n"
        "Введіть порядок денний, кожен пункт на новому рядку."
    )
    await state.set_state(AdminState.agenda)

async def set_agenda(message: types.Message, state: FSMContext, db):
    agenda = message.text.split("\n")
    session_data = await state.get_data()
    session_code = session_data["session_code"]

    db.update_agenda(session_code, agenda)
    await message.answer(
        "Порядок денний збережено. Ви можете керувати сесією.",
        reply_markup=admin_keyboard()  # Додаємо клавіатуру
    )
    await state.clear()

def register_admin_handlers(dp: Dispatcher, db):
    dp.message.register(create_session, lambda message: message.text == "Створити сесію")
    dp.message.register(set_session_name, StateFilter(AdminState.session_name))
    dp.message.register(set_session_password, StateFilter(AdminState.session_password))
    dp.message.register(set_agenda, StateFilter(AdminState.agenda))
