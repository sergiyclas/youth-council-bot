import logging
import os

import PyPDF2
from aiogram import Bot, F, Router, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.keyboards.admin import session_control_kb
from bot.keyboards.common import common_kb, pdf_kb
from config import OPTION

if str(OPTION) == 'MySQL':
    from bot.database.database import Database
else:
    from bot.database.database_postgres import Database

common_router = Router()


pdf_router = Router()

class PDFMergeStates(StatesGroup):
    uploading = State()
    merging = State()

pdf_files = {}


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
        await message.answer("Помилка: Ви не перебуваєте в активній сесії.", reply_markup=session_control_kb())
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
            "🔹 <b>/merge_pdf</b> - Об'єднати pdf-файли (макс. 5 за раз).\n"
            "🔹 <b>/post</b> - Написати пост через AI (лише для адмінів).\n"
        ),
        parse_mode="HTML"
    )


@pdf_router.message(Command("merge_pdf"))
async def start_pdf_merge(message: types.Message, state: FSMContext):
    pdf_files[message.from_user.id] = []
    await state.set_state(PDFMergeStates.uploading)
    await message.answer(
        "Скиньте PDF-файл. Ви можете завантажити до 5 файлів. Натисніть 'Об'єднати PDF', коли завершите.",
        reply_markup=pdf_kb())


@pdf_router.message(PDFMergeStates.uploading, F.document)
async def receive_pdf(message: types.Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id

    if user_id not in pdf_files:
        await message.answer("Будь ласка, спочатку введіть команду /merge_pdf.")
        return

    if len(pdf_files[user_id]) >= 5:
        await message.answer("Ліміт завантажених файлів вичерпано. Натисніть 'Об'єднати PDF'.")
        return

    if message.document.mime_type != "application/pdf":
        await message.answer("Будь ласка, надішліть саме PDF-файл.")
        return

    file_id = message.document.file_id
    file_path = f"temp_{user_id}_{len(pdf_files[user_id]) + 1}.pdf"

    file = await bot.get_file(file_id)
    await bot.download_file(file.file_path, file_path)

    pdf_files[user_id].append(file_path)
    await message.answer(
        f"Файл {message.document.file_name} додано. Ви можете додати ще {5 - len(pdf_files[user_id])} файлів.")


@pdf_router.message(PDFMergeStates.uploading, F.text == "Об'єднати PDF")
async def ask_for_pdf_name(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    if user_id not in pdf_files or len(pdf_files[user_id]) == 0:
        await state.clear()
        await message.answer("Ви не завантажили жодного PDF-файлу, тому результату нема.\n\nГарного дня",
                             reply_markup=session_control_kb())
        return

    await state.set_state("waiting_for_pdf_name")
    await message.answer("Введіть назву для об'єднаного PDF-файлу:")


@pdf_router.message(StateFilter("waiting_for_pdf_name"))
async def merge_pdfs_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    pdf_name = message.text.strip()

    if user_id not in pdf_files or len(pdf_files[user_id]) == 0:
        await message.answer("Ви не завантажили жодного PDF-файлу.")
        return

    output_filename = f"{pdf_name}.pdf"

    try:
        merger = PyPDF2.PdfMerger()
        for pdf in pdf_files[user_id]:
            merger.append(pdf)
        merger.write(output_filename)
        merger.close()

        await message.answer_document(types.FSInputFile(output_filename))
        await message.answer("Ваш PDF-файл об'єднано!\n\nУспішного використання!", reply_markup=common_kb())

    except Exception as e:
        await message.answer(f"⚠ Сталася помилка під час об'єднання PDF: {str(e)}")

    # Видалення всіх PDF-файлів
    try:
        for pdf in pdf_files[user_id]:
            if os.path.exists(pdf):
                os.remove(pdf)
        if os.path.exists(output_filename):
            os.remove(output_filename)
    except Exception as e:
        logging.error(f"Помилка при видаленні файлів: {e}")

    # Очищення списку файлів
    del pdf_files[user_id]

    await state.clear()