import logging

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.keyboards.admin import admin_menu_kb
from bot.keyboards.common import common_kb

from config import OPTION

if str(OPTION) == 'MySQL':
    from bot.database.database import Database
else:
    from bot.database.database_postgres import Database

common_router = Router()

@common_router.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    logging.info("Хендлер /start викликано")
    await state.clear()
    await message.answer(
        "Вітаю! Ось список доступних дій:",
        reply_markup=common_kb()
    )

@common_router.message(Command("info"))
@common_router.message(F.text == "ℹ️ Інформація про сесію")
@common_router.message(F.text == "Інформація про сесію")
async def session_info(message: types.Message, state: FSMContext, db: Database):
    """
    Учасник переглядає інформацію про сесію.
    """
    session_data = await state.get_data()
    logging.info(f"Дані стану для користувача {message.from_user.id}: {session_data}")

    session_code = session_data.get("session_code")
    session_name = session_data.get("session_name")

    if not session_code or not session_name:
        await message.answer("Помилка: Ви не перебуваєте в активній сесії.", reply_markup=admin_menu_kb())
        return

    # Отримуємо список учасників
    participants = await db.get_session_participants_with_names(session_code)
    participant_list = "\n".join([f"{i + 1}. {p['name']}" for i, p in enumerate(participants)])

    # Отримуємо порядок денний
    agenda = await db.get_session_agenda(session_code)
    agenda_text = "\n".join([f"{i + 1}. {item}" for i, item in enumerate(agenda)])

    await message.answer(
        f"Інформація про сесію:\n"
        f"🔑 Код: <code>{session_code}</code>\n"
        f"📋 Назва: <b>{session_name}</b>\n\n"
        f"Учасники:\n{participant_list}\n\n"
        f"Порядок денний:\n{agenda_text}",
        parse_mode="HTML"
    )


@common_router.message(Command("help"))
@common_router.message(F.text == "📋 Допомога")
@common_router.message(F.text == "Допомога")
async def help_command(message: types.Message):
    """
    Відображає коротку інформацію про бота та доступні команди.
    """
    await message.answer(
        text=(
            "Цей бот дозволяє створювати сесії, голосувати та переглядати результати.\n\n"
            "Доступні команди:\n"
            "🔹 <b>/create_session</b> - Створити сесію (для адміністратора).\n"
            "🔹 <b>/join</b> - Приєднатися до сесії (для учасника).\n"
            "🔹 <b>/info</b> - Інформація про сесію.\n"
            "🔹 <b>/leave</b> - Вийти з сесії.\n"
            "🔹 <b>/help</b> - Допомога по командах.\n"
            "🔹 <b>/post</b> - Написати пост через AI (лише для адмінів).\n"
        ),
        parse_mode="HTML"
    )
