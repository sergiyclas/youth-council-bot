from aiogram import types, Dispatcher
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from bot.keyboards.admin import voting_keyboard

class ParticipantState(StatesGroup):
    session_code = State()
    session_password = State()
    name = State()

async def join_session(message: types.Message, state: FSMContext, db):
    if message.text == "Приєднатися до сесії":
        await message.answer("Введіть код сесії:")
        await state.set_state(ParticipantState.session_code)

async def validate_code(message: types.Message, state: FSMContext, db):
    session_code = message.text
    session = db.get_session(session_code)

    if not session:
        await message.answer("Сесія не знайдена. Введіть код ще раз або перевірте його.")
        return

    await state.update_data(session_code=session_code)
    await message.answer("Введіть пароль до сесії:")
    await state.set_state(ParticipantState.session_password)

async def validate_password(message: types.Message, state: FSMContext, db):
    password = message.text
    session_data = await state.get_data()
    session_code = session_data["session_code"]

    session = db.get_session(session_code)
    if session["password"] != password:
        await message.answer("Неправильний пароль. Спробуйте ще раз.")
        return

    await message.answer("Введіть ваше ім'я:")
    await state.set_state(ParticipantState.name)

async def save_participant(message: types.Message, state: FSMContext, db):
    name = message.text
    session_data = await state.get_data()
    session_code = session_data["session_code"]

    db.add_participant(session_code, message.from_user.id, name)
    await message.answer("Ви приєдналися до сесії. Чекайте початку голосування.")
    await state.clear()

def register_participant_handlers(dp: Dispatcher, db):
    dp.message.register(join_session, lambda message: message.text == "Приєднатися до сесії")
    dp.message.register(validate_code, StateFilter(ParticipantState.session_code))
    dp.message.register(validate_password, StateFilter(ParticipantState.session_password))
    dp.message.register(save_participant, StateFilter(ParticipantState.name))
