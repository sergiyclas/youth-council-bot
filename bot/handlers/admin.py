import logging
import os
import re

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command, StateFilter
from aiogram.types import FSInputFile

from bot.common.ai import generate_post, client
from bot.common.utils import generate_protocol, generate_attendance_list_full
from bot.keyboards.admin import admin_menu_kb, session_control_kb, admin_vote_kb, force_end_vote_kb, admin_end_vote_kb, \
    set_rv_name, yes_no_kb, set_session_type_kb, admin_fea_kb
from random import randint
from bot.keyboards.common import vote_kb, common_kb

from config import OPTION

if str(OPTION) == 'MySQL':
    from bot.database.database import Database
else:
    from bot.database.database_postgres import Database

ALLOWED_ADMINS = {1014099963}

admin_router = Router()


class AdminStates(StatesGroup):
    session_name = State()
    session_password = State()
    admin_name = State()
    session_agenda = State()
    agenda_question = State()
    youth_council_name = State()
    youth_council_city = State()
    youth_council_region = State()
    youth_council_head = State()
    youth_council_secretary = State()

class AdminState(StatesGroup):
    in_admin = State()
    waiting_for_session_code = State()
    waiting_for_user_id = State()


@admin_router.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    logging.info("Хендлер /start викликано")
    await state.clear()
    await message.answer(
        "Вітаю! Ось список доступних дій:",
        reply_markup=common_kb()
    )


@admin_router.message(F.text == "Створити сесію")
@admin_router.message(Command("create_session"))
async def create_session(message: types.Message, state: FSMContext):
    logging.info("Користувач починає створення сесії")
    await message.answer("Введіть ім'я сесії:")
    await state.set_state(AdminStates.session_name)


@admin_router.message(AdminStates.session_name)
async def set_session_name(message: types.Message, state: FSMContext):
    session_name = message.text.strip()

    ignored_texts = ["🔄 Змінити порядок денний", "✅ Почати голосування по питаннях порядку денного", "❌ Завершити сесію",
                     "⚙️ Налаштувати інформацію про МР", "ℹ️ Інформація про сесію", "/help", "/post", "/join",
                     "/create_session", "/leave", "/merge_pdf", "/info"]

    # Перевіряємо, чи текст є текстом кнопки
    if session_name in ignored_texts:
        await message.answer("Будь ласка, введіть назву сесії, а не натискайте кнопки.")
        return

    logging.info(f"Отримано ім'я сесії: {session_name}")
    await state.update_data(session_name=session_name)
    await message.answer("Введіть пароль для сесії:")
    await state.set_state(AdminStates.session_password)


@admin_router.message(AdminStates.session_password)
async def set_session_password(message: types.Message, state: FSMContext, db: Database):
    session_password = message.text.strip()

    if len(session_password) > 20:
        await message.answer("Пароль занадто довгий, максимум 20 символів")
        return

    logging.info(f"Отримано пароль сесії: {session_password}")
    await state.update_data(session_password=session_password)

    # Генеруємо унікальний код сесії
    session_code = randint(1000, 9999)
    session_data = await state.get_data()
    logging.info(f"Генеруємо код сесії: {session_code}")

    # Перевіряємо, чи вже є сесія з таким номером
    existing_session = await db.get_session_by_code(session_code)
    if existing_session:
        logging.info(f"Видаляємо існуючу сесію: {session_code}")
        await db.delete_session(session_code)  # Видаляємо сесію
        await db.delete_related_data(session_code)  # Видаляємо всі пов'язані дані

    # Зберігаємо нову сесію в базі даних
    await db.add_session(
        session_code=session_code,
        session_name=session_data['session_name'],
        session_password=session_password,
        admin_id=message.from_user.id
    )

    # Оновлюємо session_code у стані
    await state.update_data(session_code=session_code)

    logging.info(f"Сесія створена: {session_data['session_name']} з кодом {session_code}")
    await message.answer(
        f"Сесія створена! \nКод сесії: <code>{session_code}</code>\nПароль: <code>{session_password}</code>",
        parse_mode="HTML"
    )
    await message.answer("Введіть ваше ім'я для участі в сесії:")
    await state.set_state(AdminStates.admin_name)



@admin_router.message(AdminStates.admin_name)
async def set_admin_name(message: types.Message, state: FSMContext, db: Database):
    admin_name = message.text.strip()
    session_data = await state.get_data()

    session_code = session_data.get("session_code")
    if not session_code:
        await message.answer("Помилка: код сесії не знайдено.")
        return

    # Додаємо адміністратора як учасника
    await db.add_participant(
        session_code=session_code,
        user_id=message.from_user.id,
        user_name=admin_name
    )

    logging.info(f"Адміністратор {admin_name} доданий до сесії {session_code}")
    await message.answer(
        f"Дякуємо, {admin_name}! Ви успішно створили сесію та приєдналися до неї.",
        reply_markup=session_control_kb()
    )
    await message.answer("Введіть порядок денний (кожен пункт з нового рядка):")
    await state.set_state(AdminStates.session_agenda)


@admin_router.message(AdminStates.session_agenda)
async def set_agenda(message: types.Message, state: FSMContext, db: Database):
    session_data = await state.get_data()

    # Тексти кнопок, які потрібно ігнорувати
    ignored_texts = [
        "🔄 Змінити порядок денний", "✅ Почати голосування по питаннях порядку денного",
        "❌ Завершити сесію", "⚙️ Налаштувати інформацію про МР", "ℹ️ Інформація про сесію"
    ]

    # Якщо натиснута кнопка, виводимо повідомлення
    if message.text in ignored_texts:
        await message.answer("Будь ласка, введіть новий порядок денний, а не натискайте кнопки.")
        return

    # Перевіряємо, чи є session_name і session_code у стані
    session_name = session_data.get('session_name')
    session_code = session_data.get('session_code')

    if not session_name or not session_code:
        await message.answer("Помилка: сесія не знайдена. Будь ласка, почніть з початку.")
        logging.error("Сесія не знайдена у стані")
        return

    # Розбиваємо введений текст по рядках та очищаємо кожен рядок
    raw_agenda = message.text.split("\n")
    agenda = []

    for line in raw_agenda:
        clean_line = line.strip()

        # Видаляємо першу нумерацію (якщо є), наприклад: "1. Текст" або "2) Текст"
        clean_line = re.sub(r"^\d+[.)]\s*", "", clean_line)

        # Додаємо у список тільки, якщо рядок не пустий
        if clean_line:
            agenda.append(clean_line)

    # Перевірка на дублікати
    duplicate_items = {item for item in agenda if agenda.count(item) > 1}
    if duplicate_items:
        duplicates_text = "\n".join(duplicate_items)
        await message.answer(
            f"❌ Помилка: у порядку денному є дублікати питань:\n<b>{duplicates_text}</b>\n"
            "Будь ласка, виправте та введіть знову.",
            parse_mode="HTML"
        )
        return

    logging.info(f"Отримано новий порядок денний для сесії {session_name}: {agenda}")

    # Зберігаємо його в базу даних
    await db.set_session_agenda(session_code=session_code, agenda=agenda)

    # Форматуємо порядок денний для копіювання
    agenda_html = "<b>Порядок денний:</b>\n" + "\n".join(
        [f"{i + 1}. {item}" for i, item in enumerate(agenda)]
    )

    await message.answer(
        f"✅ Порядок денний оновлено.\n\n{agenda_html}\n\nДалі ви можете:",
        reply_markup=session_control_kb(),
        parse_mode="HTML"
    )
    logging.info(f"Порядок денний збережено для сесії {session_name}")
    await state.clear()
    await state.update_data(session_code=session_code, session_name=session_name, agenda=agenda)


@admin_router.message(F.text == "⚙️ Налаштувати інформацію про МР")
async def set_information_about_youth_council(message: types.Message, state: FSMContext, db: Database):
    admin_id = message.from_user.id

    result = await db.get_youth_council_info(admin_id)

    if result:
        council_info = result
        text = (f"Інформація про МР вже заповнена:\n\n"
                f"Назва: {council_info.name}\n"
                f"Місто: {council_info.city}\n"
                f"Регіон: {council_info.region}\n"
                f"Голова: {council_info.head}\n"
                f"Секретар: {council_info.secretary}\n\n"
                "Бажаєте змінити інформацію?")

        await message.answer(text, reply_markup=yes_no_kb())
    else:
        await message.answer("Заповніть інформацію про МР. \n\nВведіть назву Молодіжної ради:")
        await state.set_state(AdminStates.youth_council_name)


@admin_router.message(F.text == "Так")
async def restart_youth_council_info(message: types.Message, state: FSMContext):
    await message.answer("Введіть назву МР:")
    await state.set_state(AdminStates.youth_council_name)


@admin_router.message(F.text == "Ні")
async def cancel_youth_council_update(message: types.Message, state: FSMContext, db: Database):
    session_data = await state.get_data()

    session_name = session_data.get('session_name')
    session_code = session_data.get('session_code')

    current_question_index = await db.get_current_question_index(session_code)
    agenda = await db.get_session_agenda(session_code)

    if len(agenda) > current_question_index + 1:
        await message.answer("Налаштування інформації про МР скасовано.", reply_markup=session_control_kb())
        await state.clear()
        await state.update_data(session_code=session_code, session_name=session_name, agenda=agenda, current_question_index=current_question_index)
        return

    await message.answer(
        "Усі питання розглянуті. Ви можете завершити сесію.",
        reply_markup=admin_end_vote_kb()
    )
    await state.clear()
    await state.set_state("admin_control")
    await state.update_data(session_code=session_code, session_name=session_name, agenda=agenda, current_question_index=current_question_index)
    return


@admin_router.message(AdminStates.youth_council_name)
async def set_youth_council_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer("Введіть місто:")
    await state.set_state(AdminStates.youth_council_city)


@admin_router.message(AdminStates.youth_council_city)
async def set_youth_council_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text.strip())
    await message.answer("Введіть регіон:")
    await state.set_state(AdminStates.youth_council_region)


@admin_router.message(AdminStates.youth_council_region)
async def set_youth_council_region(message: types.Message, state: FSMContext):
    await state.update_data(region=message.text.strip())
    await message.answer("Введіть голову засідання:")
    await state.set_state(AdminStates.youth_council_head)


@admin_router.message(AdminStates.youth_council_head)
async def set_youth_council_head(message: types.Message, state: FSMContext):
    await state.update_data(head=message.text.strip())
    await message.answer("Введіть секретаря засідання:")
    await state.set_state(AdminStates.youth_council_secretary)


@admin_router.message(AdminStates.youth_council_secretary)
async def set_youth_council_secretary(message: types.Message, state: FSMContext, db: Database):
    session_data = await state.get_data()
    admin_id = message.from_user.id

    session_name = session_data.get('session_name')
    session_code = session_data.get('session_code')

    await db.save_youth_council_info(
        user_id=admin_id,
        name=session_data["name"],
        city=session_data["city"],
        region=session_data["region"],
        head=session_data["head"],
        secretary=message.text.strip()
    )

    current_question_index = await db.get_current_question_index(session_code)
    agenda = await db.get_session_agenda(session_code)

    if len(agenda) > current_question_index + 1:
        await message.answer("Інформація про МР збережена!", reply_markup=session_control_kb())
        await state.clear()
        await state.update_data(session_code=session_code, session_name=session_name, agenda=agenda, current_question_index=current_question_index)
        return


    await message.answer(
        "Усі питання розглянуті. Ви можете завершити сесію.",
        reply_markup=admin_end_vote_kb()
    )
    await state.clear()
    await state.set_state("admin_control")
    await state.update_data(session_code=session_code, session_name=session_name, agenda=agenda, current_question_index=current_question_index)
    return


@admin_router.message(F.text == "🔄 Змінити порядок денний")
async def change_agenda(message: types.Message, state: FSMContext):
    session_data = await state.get_data()

    session_name = session_data.get('session_name')
    session_code = session_data.get('session_code')

    if not session_name or not session_code:
        await message.answer("Помилка: сесія не знайдена. Будь ласка, створіть нову сесію.")
        logging.error("Сесія не знайдена у стані")
        return

    logging.info(f"Користувач змінює порядок денний для сесії {session_name}")
    await message.answer("Введіть новий порядок денний (кожен пункт з нового рядка):")
    await state.set_state(AdminStates.session_agenda)


@admin_router.message(F.text == "✅ Почати голосування по питаннях порядку денного")
async def start_voting(message: types.Message, state: FSMContext, db: Database):
    session_data = await state.get_data()

    session_code = session_data.get("session_code")
    if not session_code:
        await message.answer("Помилка: сесія не знайдена.")
        return

    # Отримуємо порядок денний
    agenda = await db.get_session_agenda(session_code)
    if not agenda:
        await message.answer("Порядок денний порожній.")
        return

    # Зберігаємо питання у стані
    await state.update_data(agenda=agenda, current_question_index=0)

    # Починаємо голосування за перше питання
    current_question = agenda[0]

    await db.close_session(session_code)

    # Надсилаємо питання всім учасникам сесії
    participants = await db.get_session_participants(session_code)
    for participant_id in participants:
        # Відправляємо голосування учасникам
        await message.bot.send_message(
            chat_id=participant_id,
            text=f"📋 Перше питання для голосування:\n<b>{current_question}</b>\n\nОберіть один із варіантів: 'За', 'Проти', 'Утримався'",
            parse_mode="HTML",
            reply_markup=vote_kb()
        )
    await state.set_state("voting")


@admin_router.message(StateFilter("voting"), F.text.in_({"За", "Проти", "Утримаюсь"}))
async def collect_votes(message: types.Message, state: FSMContext, db: Database):
    print('collect_votes')
    session_data = await state.get_data()
    print(session_data)

    # Отримуємо session_code
    session_code = session_data.get("session_code")
    if not session_code:
        await message.answer("Помилка: Сесія не знайдена.")
        return

    # Отримуємо поточне питання та порядок денний із бази даних
    current_question_index = await db.get_current_question_index(session_code)
    agenda = await db.get_session_agenda(session_code)

    if current_question_index is None or not agenda or current_question_index >= len(agenda):
        await message.answer("Помилка: Питання не знайдені.")
        return

    current_question = agenda[current_question_index]

    # Перевіряємо, чи користувач уже голосував за це питання
    user_voted = await db.has_user_voted(
        session_code=session_code,
        user_id=message.from_user.id,
        question=current_question
    )

    admin_id = await db.get_admin_id(session_code)

    force_close = False
    if message.text == "Завершити опитування по поточному питанню" and admin_id == message.from_user.id:
        force_close = True

    if user_voted and not force_close:
        print(current_question, user_voted)
        await message.answer("Ви вже проголосували за це питання. Дочекайтеся завершення голосування.", reply_markup=types.ReplyKeyboardRemove())
        return

    if not force_close and not user_voted:
    # Зберігаємо голос
        await db.add_vote(
            session_code=session_code,
            user_id=message.from_user.id,
            question=current_question,
            vote=message.text
        )
        await message.answer("Ваш голос зараховано.", reply_markup=types.ReplyKeyboardRemove())

    all_votes_collected = await db.check_all_votes_collected(session_code, current_question)
    if all_votes_collected or force_close:
        # Отримуємо результати голосування
        vote_results = await db.get_vote_results(session_code, current_question)
        count_participants = await db.count_of_participants(session_code)
        vote_results['Не голосували'] = count_participants - sum(vote_results.values())
        results_text = "\n".join(
            [f"<b>{key}</b>: {value}" for key, value in vote_results.items()]
        )

        decision = "Не ухвалено"
        if int(vote_results['За']) * 2 > count_participants:
            decision = "Ухвалено"

        # Надсилаємо результати всім учасникам
        participants = await db.get_session_participants(session_code)
        for participant_id in participants:
            await message.bot.send_message(
                chat_id=participant_id,
                text=f"Голосування завершено для питання:\n<b>{current_question_index + 1}. {current_question}</b>\n\nРезультати:\n{results_text}\n\nРішення було <b>{decision}</b>",
                parse_mode="HTML",
                reply_markup=types.ReplyKeyboardRemove()
            )

        await message.bot.send_message(
            chat_id=admin_id,
            text=f"Введіть Прізвище та Ім'я людини, яка запропонувала це питання:",
            reply_markup=types.ReplyKeyboardRemove()
        )

        if admin_id == message.from_user.id:
            await state.set_state("proposer_entry")

        # await message.bot.send_message(
        #     chat_id=admin_id,
        #     text=f"Оберіть наступну дію:",
        #     reply_markup=admin_vote_kb()
        # )

        # await db.set_current_question_index(session_code, current_question_index + 1)
        # await state.set_state("voting")
    else:
        if message.from_user.id == admin_id:
            await message.answer(
                "Не всі проголосували. Ви можете дочекатися або завершити голосування вручну.",
                reply_markup=force_end_vote_kb()
            )
            await state.set_state("proposer_entry")


# @admin_router.message(StateFilter("proposer_entry"))
# async def set_proposer_name(message: types.Message, state: FSMContext, db: Database):
#


@admin_router.message(StateFilter("proposer_entry"))
async def force_end_vote_and_set_proposed_entry(message: types.Message, state: FSMContext, db: Database):
    session_data = await state.get_data()
    session_code = session_data.get("session_code")
    current_question_index = session_data.get("current_question_index", 0)
    agenda = session_data.get("agenda", [])

    if not session_code or current_question_index is None or not agenda:
        await message.answer("Помилка: сесія або питання не знайдені.")
        return

    current_question = agenda[current_question_index]
    admin_id = await db.get_admin_id(session_code)

    current_question_index = await db.get_current_question_index(session_code)

    if current_question_index is None:
        await message.answer("Номер питання не був знайденим")
        return

    proposer_name = message.text.strip() if message.text else ''

    if message.text.strip() == "Завершити опитування по поточному питанню":
        vote_results = await db.get_vote_results(session_code, current_question)
        count_participants = await db.count_of_participants(session_code)
        vote_results['Не голосували'] = count_participants - sum(vote_results.values())
        results_text = "\n".join(
            [f"<b>{key}</b>: {value}" for key, value in vote_results.items()]
        )

        decision = "Не ухвалено"
        if int(vote_results['За']) * 2 > count_participants:
            decision = "Ухвалено"

        # Відправляємо результати всім учасникам
        participants = await db.get_session_participants(session_code)
        for participant_id in participants:
            await message.bot.send_message(
                chat_id=participant_id,
                text=f"Голосування завершено для питання:\n<b>{current_question_index + 1}. {current_question}</b>\n\nРезультати:\n{results_text}\n\nРішення було <b>{decision}</b>",
                parse_mode="HTML",
                reply_markup=types.ReplyKeyboardRemove()
            )

        await message.bot.send_message(
            chat_id=admin_id,
            text=f"Введіть Прізвище та Ім'я людини, яка запропонувала це питання:",
            reply_markup=types.ReplyKeyboardRemove()
        )

    else:
        logging.info(f"Зайшло в функцію встановлення імені для питання")

        agenda = await db.get_session_agenda(session_code)

        if not agenda or current_question_index >= len(agenda):
            await message.answer("Помилка: Питання/agenda не знайдені.")
            return

        await db.set_agenda_item_proposer(session_code, current_question, proposer_name)
        await message.answer("Ім'я збережено✅.")

        logging.info(f"Відповідальна особа {proposer_name} записана для питання {current_question}")

        if len(agenda) > current_question_index + 1:
            new_question = agenda[current_question_index + 1]
            await message.bot.send_message(
                chat_id=admin_id,
                text=f"Голосуємо за наступне питання порядку денного?\n\n<b>{current_question_index + 2}. {new_question}</b>\n\nОберіть дію: ",
                reply_markup=admin_vote_kb()
            )

        else:
            youth_council_info = await db.get_youth_council_info(admin_id)

            text = ""
            if youth_council_info:
                council_info = youth_council_info
                text = (f"Інформація про МР:\n"
                        f"Назва: {council_info.name}\n"
                        f"Місто: {council_info.city}\n"
                        f"Регіон: {council_info.region}\n"
                        f"Голова: {council_info.head}\n"
                        f"Секретар: {council_info.secretary}\n\n"
                        )

            await message.bot.send_message(
                chat_id=admin_id,
                text=f"{text}Усі питання розглянуті. Ви можете завершити сесію.",
                reply_markup=admin_end_vote_kb()
            )

        await db.set_current_question_index(session_code, current_question_index + 1)
        await state.set_state('voting')


@admin_router.message(StateFilter("voting"), F.text == "Голосувати за наступне питання")
async def next_question(message: types.Message, state: FSMContext, db: Database):
    session_data = await state.get_data()

    session_code = session_data.get("session_code")
    current_question_index = session_data.get("current_question_index", 0)
    agenda = session_data.get("agenda", [])

    if current_question_index + 1 >= len(agenda):
        admin_id = message.from_user.id
        youth_council_info = await db.get_youth_council_info(admin_id)

        text = ""
        if youth_council_info:
            council_info = youth_council_info
            text = (f"Інформація про МР:\n"
                    f"Назва: {council_info.name}\n"
                    f"Місто: {council_info.city}\n"
                    f"Регіон: {council_info.region}\n"
                    f"Голова: {council_info.head}\n"
                    f"Секретар: {council_info.secretary}\n\n"
                    )

        await message.answer(
            f"{text}Усі питання розглянуті. Ви можете завершити сесію.",
            reply_markup=admin_end_vote_kb()
        )
        return

    # Переходимо до наступного питання
    next_question_index = current_question_index + 1
    next_question_from_agenda = agenda[next_question_index]

    # Надсилаємо питання всім учасникам сесії
    participants = await db.get_session_participants(session_code)
    for participant_id in participants:
        await message.bot.send_message(
            chat_id=participant_id,
            text=f"📋 Голосування по питанню <b>{next_question_index + 1}</b>:\n<b>{next_question_index + 1}. {next_question_from_agenda}</b>\n\nОберіть один із варіантів: 'За', 'Проти', 'Утримався'",
            parse_mode="HTML",
            reply_markup=vote_kb()
        )

    await state.update_data(current_question_index=next_question_index)


@admin_router.message(F.text == "📝 Заповнити родові відмінки імен")
async def start_filling_name_cases(message: types.Message, state: FSMContext, db: Database):
    user_id = message.from_user.id
    session_data = await state.get_data()
    session_code = session_data.get("session_code")

    if not session_code:
        await message.answer("Помилка: сесія не знайдена.")
        return

    proposed_names = await db.get_proposed_names_by_admin(session_code, user_id)

    if not proposed_names:
        await message.answer("Ви не вводили імен під час цієї сесії.")
        return

    await state.update_data(proposed_names=proposed_names, current_index=0)
    await process_next_name(message, state, db)

async def process_next_name(message: types.Message, state: FSMContext, db: Database):
    session_data = await state.get_data()
    proposed_names = session_data.get("proposed_names", [])
    current_index = session_data.get("current_index", 0)

    session_code = session_data.get("session_code")
    session_name = session_data.get("session_name")

    if current_index >= len(proposed_names):
        await state.clear()
        await state.update_data(session_code=session_code, session_name=session_name)
        await message.answer("Усі імена перевірені та оновлені!\n\nВертаємося до закінчення голосування", reply_markup=admin_end_vote_kb())
        return

    current_name = proposed_names[current_index]
    existing_name = await db.get_name_rv(message.from_user.id, current_name)

    if existing_name and existing_name.name_rv:
        await state.update_data(current_name=current_name)
        await message.answer(
            f"Ім'я <b>{current_name}</b> вже має родовий відмінок: <b>{existing_name.name_rv}</b>\n\n"
            "Якщо бажаєте залишити цей варіант, то нажміть <b>Пропустити</b>, якщо ні, то напишіть Ваш варіант:",
            parse_mode="HTML",
            reply_markup=set_rv_name()
        )
    else:
        await state.update_data(current_name=current_name)
        await message.answer(
            f"Ім'я <b>{current_name}</b> не має родового відмінку.\n\n"
            "Введіть родовий відмінок або натисніть <b>'Пропустити'</b>, щоб не пропустити це ім'я.",
            parse_mode="HTML",
            reply_markup=set_rv_name()
        )

    await state.set_state("waiting_for_rv")

@admin_router.message(StateFilter("waiting_for_rv"), F.text == "Пропустити")
async def keep_existing_rv(message: types.Message, state: FSMContext, db: Database):
    session_data = await state.get_data()
    current_index = session_data.get("current_index", 0)

    await state.update_data(current_index=current_index + 1)
    await process_next_name(message, state, db)

@admin_router.message(StateFilter("waiting_for_rv"))
async def update_name_rv(message: types.Message, state: FSMContext, db: Database):
    session_data = await state.get_data()
    current_name = session_data.get("current_name")
    current_index = session_data.get("current_index", 0)

    await db.update_name_rv(message.from_user.id, current_name, message.text.strip())
    await message.answer(f"Родовий відмінок для імені <b>{current_name}</b> тепер <b>{message.text.strip()}</b>!", parse_mode="HTML")

    await state.update_data(current_index=current_index + 1)
    await process_next_name(message, state, db)


@admin_router.message(F.text == "❌ Завершити сесію")
async def initiate_end_session(message: types.Message, state: FSMContext, db: Database):
    session_data = await state.get_data()
    session_name = session_data.get('session_name')
    session_code = session_data.get("session_code")

    if not session_code:
        await message.answer("Помилка: сесія не знайдена.")
        return

    admin_id = message.from_user.id
    youth_council_info = await db.get_youth_council_info(admin_id)

    if not youth_council_info:
        await message.answer(
            "У Вас не заповнена інформація про Молодіжну раду. \nПочинаємо заповнення! \n\nВведіть назву МР:")
        await state.set_state(AdminStates.youth_council_name)
        return

    await state.update_data(session_code=session_code, session_name=session_name)
    await message.answer("Введіть номер засідання/протоколу:")
    await state.set_state("waiting_for_protocol_number")


@admin_router.message(StateFilter("waiting_for_protocol_number"))
async def ask_for_session_type(message: types.Message, state: FSMContext):
    protocol_number = message.text.strip()
    await state.update_data(protocol_number=protocol_number)

    await message.answer("Введіть тип засідання (можна власний варіант, просто напишіть його, тільки у форматі, що відповідає на питання 'якого?'):", reply_markup=set_session_type_kb())
    await state.set_state("waiting_for_session_type")


@admin_router.message(StateFilter("waiting_for_session_type"))
async def finalize_session_details(message: types.Message, state: FSMContext, db: Database):
    session_data = await state.get_data()
    session_code = session_data.get("session_code")
    session_name = session_data.get("session_name")
    protocol_number = session_data.get("protocol_number")
    session_type = message.text.strip()

    await db.update_session_details(session_code, protocol_number, session_type)
    await complete_session(message, session_code, session_name, state, db)

async def complete_session(message: types.Message, session_code: str, session_name: str, state: FSMContext,
                           db: Database):
    results = await db.end_session(session_code)
    total_participants = await db.count_of_participants(session_code)
    results_text = "\n".join([
        f"<b>{index + 1}. {question}</b>\nЗа: {votes['for']}, Проти: {votes['against']}, Утримались: {votes['abstain']}, Не голосували: {votes['not_voted']}\nЦе рішення було <b>{'Прийнято' if votes['for'] * 2 > total_participants else 'Не прийнято'}</b>"
        for index, (question, votes) in enumerate(results.items())
    ])

    try:
        protocol_path = await generate_protocol(session_code, db)
        attendance_list_path = await generate_attendance_list_full(session_code, db)

        protocol_file = FSInputFile(protocol_path)
        await message.answer_document(document=protocol_file)

        attendance_file = FSInputFile(attendance_list_path)
        await message.answer_document(document=attendance_file)

        # Видалення файлів після відправки
        os.remove(protocol_path)
        os.remove(attendance_list_path)
        logging.info(f"Файли {protocol_path} та {attendance_list_path} були видалені.")
    except Exception as e:
        logging.error(f"Помилка під час генерації документів: {e}")
        await message.answer(f"Сталася помилка під час генерації документів: {str(e)}")

    participants = await db.get_session_participants(session_code)
    for participant_id in participants:
        await message.bot.send_message(
            chat_id=participant_id,
            text=f"Сесію <b>{session_name}</b> завершено. \nРезультати голосування:\n\n{results_text}",
            parse_mode="HTML"
        )

    await message.answer(
        f"Сесію <b>{session_name}</b> завершено. Результати розіслані всім учасникам.",
        parse_mode="HTML", reply_markup=admin_menu_kb()
    )
    await state.clear()



@admin_router.message(F.text == "Написати пост")
@admin_router.message(Command("post"))
async def create_session(message: types.Message, state: FSMContext):
    logging.info(f"Користувач {message.from_user.id} починає написання посту через ШІ")

    if str(message.from_user.id) not in ['1014099963', '1762778352']:
        await message.answer("У вас нема прав")

    await message.answer("Вставте інформацію з якої слід згенерувати пост:")
    await state.set_state("waiting")

@admin_router.message(StateFilter("waiting"))
async def send_generated_post(message: types.Message, state: FSMContext):
    text = message.text
    logging.info(f"Згенеровано {text}")

    await message.reply("Генерую пост, зачекайте...")

    post = await generate_post(client, text)

    if post:
        await message.reply(f"{post}")
    else:
        await message.reply("На жаль, не вдалося згенерувати пост. Спробуйте пізніше.")

    await state.clear()


@admin_router.message(Command("admin_fea"))
async def enter_admin_panel(message: types.Message, state: FSMContext):
    """Перевіряє доступ і переводить в стан адмінки"""
    if message.from_user.id not in ALLOWED_ADMINS:
        await message.answer("Not allowed", reply_markup=common_kb())
        return

    await state.set_state(AdminState.in_admin)
    await message.answer("✅ Ви увійшли в адмін-панель. Виберіть команду:", reply_markup=admin_fea_kb())

# ---- ВИХІД З АДМІН-ПАНЕЛІ ---- #
@admin_router.message(F.text == "/exit_admin")
async def exit_admin_panel(message: types.Message, state: FSMContext):
    """Вихід з адмін-панелі"""
    await state.clear()
    await message.answer("🚪 Ви вийшли з адмін-панелі.", reply_markup=common_kb())

# ---- ПОКАЗ ОСТАННІХ 10 СЕСІЙ ---- #
@admin_router.message(AdminState.in_admin, Command("show_recent"))
async def show_recent_sessions(message: types.Message, db: Database):
    """Відображає статистику останніх 10 сесій"""
    sessions = await db.get_last_sessions(10)

    if not sessions:
        await message.answer("❌ Немає останніх сесій.", reply_markup=admin_fea_kb())
        return

    response = "<b>📊 Останні 10 сесій:</b>\n"
    for index, session in enumerate(sessions):
        admin_name = await db.get_admin_name(session.admin_id)
        participants_count = await db.get_participant_count(session.id)
        questions_count = await db.get_questions_count(session.id)
        youth_info = await db.get_youth_council_info(session.admin_id)

        response += (
            f"\n<b>📌{index + 1}. Сесія:</b> {session.name} (Код: {session.code})"
            f"\n<b>👤 Адмін:</b> {admin_name} (ID: {session.admin_id})"
            f"\n<b>❓ Питань розглянуто:</b> {questions_count}"
            f"\n<b>👥 Учасників:</b> {participants_count}"
            f"\n<b>🏛 Молодіжна рада:</b> {youth_info.name if youth_info else 'Немає'}"
            f"\n<b>🧑‍⚖ Голова:</b> {youth_info.head if youth_info else 'Немає'}"
            f"\n<b>📅 Дата:</b> {session.date}\n\n"
        )

    await message.answer(response, parse_mode="HTML", reply_markup=admin_fea_kb())


# ---- ЗАВАНТАЖЕННЯ СЕСІЇ ---- #
@admin_router.message(AdminState.in_admin, Command("upload_session"))
async def request_session_code(message: types.Message, state: FSMContext):
    """Запитує код сесії для завантаження"""
    await message.answer("✍ Введіть код засідання:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(AdminState.waiting_for_session_code)


@admin_router.message(AdminState.waiting_for_session_code)
async def fetch_session_details(message: types.Message, state: FSMContext, db: Database):
    """Отримує повну інформацію про сесію та генерує протокол і відвідуваність"""
    try:
        session_code = int(message.text.strip())  # Примусове приведення до int
    except ValueError:
        await message.answer("❌ Код сесії має бути числом!", reply_markup=admin_fea_kb())
        await state.set_state(AdminState.in_admin)
        return

    session = await db.get_session_by_code(session_code)

    if not session:
        await message.answer("❌ Сесію не знайдено.", reply_markup=admin_fea_kb())
        await state.set_state(AdminState.in_admin)
        return

    # Отримання пов'язаних даних
    admin_name = await db.get_admin_name(session.admin_id)
    participants_count = await db.get_participant_count(session.id)
    questions_count = await db.get_questions_count(session.id)
    youth_info = await db.get_youth_council_info(session.admin_id)
    agenda_items = await db.get_agenda_items(session.id)

    agenda_text = "\n".join([
        f"<b>{index + 1}. {item.description}</b> (Запропоновано: {item.proposed})"
        for index, item in enumerate(agenda_items)
    ]) if agenda_items else "❌ Порядок денний відсутній."

    # Генерація документів
    try:
        protocol_path = await generate_protocol(session_code, db)
        attendance_list_path = await generate_attendance_list_full(session_code, db)

        protocol_file = FSInputFile(protocol_path)
        attendance_file = FSInputFile(attendance_list_path)

        await message.answer_document(document=protocol_file, caption="📜 Протокол сесії")
        await message.answer_document(document=attendance_file, caption="📝 Відвідуваність")

        # Видалення файлів після відправки
        os.remove(protocol_path)
        os.remove(attendance_list_path)

    except Exception as e:
        logging.error(f"Помилка при генерації документів: {e}")
        await message.answer(f"⚠ Сталася помилка під час генерації документів: {str(e)}", reply_markup=admin_fea_kb())

    # Відправлення повної інформації про сесію
    response = (
        f"<b>📌 Сесія:</b> {session.name} (Код: {session.code})\n"
        f"<b>📅 Дата:</b> {session.date}\n"
        f"<b>🔢 Номер сесії:</b> {session.number or 'Немає'}\n"
        f"<b>🛠 Тип сесії:</b> {session.session_type or 'Не вказано'}\n"
        f"<b>👤 Адмін:</b> {admin_name} (ID: {session.admin_id})\n"
        f"<b>📜 Питань розглянуто:</b> {questions_count}\n"
        f"<b>👥 Кількість учасників:</b> {participants_count}\n"
        f"<b>🏛 Молодіжна рада:</b> {youth_info.name if youth_info else 'Немає'}\n"
        f"<b>📍 Регіон:</b> {youth_info.region if youth_info else 'Немає'}\n"
        f"<b>🌆 Місто:</b> {youth_info.city if youth_info else 'Немає'}\n"
        f"<b>🧑‍⚖ Голова:</b> {youth_info.head if youth_info else 'Немає'}\n"
        f"<b>📋 Секретар:</b> {youth_info.secretary if youth_info else 'Немає'}\n\n"
        f"<b>📋 Порядок денний:</b>\n{agenda_text}"
    )

    await message.answer(response, parse_mode="HTML", reply_markup=admin_fea_kb())

    await state.set_state(AdminState.in_admin)


# ---- ІНФОРМАЦІЯ ПРО КОРИСТУВАЧА ---- #
@admin_router.message(AdminState.in_admin, Command("info_user"))
async def request_user_id(message: types.Message, state: FSMContext):
    """Запитує ID користувача"""
    await message.answer("✍ Введіть ID користувача:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(AdminState.waiting_for_user_id)

@admin_router.message(AdminState.waiting_for_user_id)
async def fetch_user_info(message: types.Message, state: FSMContext, db: Database):
    """Виводить статистику по користувачу"""
    try:
        user_id = int(message.text.strip())

    except ValueError:
        await message.answer("❌ Код сесії має бути числом!", reply_markup=admin_fea_kb())
        await state.set_state(AdminState.in_admin)
        return

    user_stats = await db.get_user_statistics(user_id)

    if not user_stats:
        await message.answer("❌ Користувач не знайдений.", reply_markup=admin_fea_kb())
        await state.set_state(AdminState.in_admin)
        return

    response = (
        f"<b>👤 Користувач:</b> {user_stats['name']} (ID: {user_stats['user_id']})\n"
        f"<b>🎭 Участь у сесіях:</b> {user_stats['participation_count']}\n"
        f"<b>🛠 Адміністрував сесії:</b> {user_stats['admin_count']}\n\n"
        f"<b>🏛 Топ-3 молодіжні ради:</b>\n{user_stats['top_youth_councils']}"
    )

    await message.answer(response, parse_mode="HTML", reply_markup=admin_fea_kb())
    await state.set_state(AdminState.in_admin)

# ---- ВИВІД ВСІХ КОРИСТУВАЧІВ (МАКС 30) ---- #
@admin_router.message(Command("id_all_users"))
async def list_all_users(message: types.Message, db: Database):
    """Виводить список до 30 користувачів"""
    users = await db.get_all_users(limit=30)

    if not users:
        await message.answer("❌ Користувачів не знайдено.", reply_markup=admin_fea_kb())
        return

    response = "<b>📜 Список користувачів:</b>\n"
    for user_id, name in users:
        response += f"🆔 ID: {user_id} | 🏷 Ім'я: {name}\n"

    await message.answer(response, parse_mode="HTML", reply_markup=admin_fea_kb())
