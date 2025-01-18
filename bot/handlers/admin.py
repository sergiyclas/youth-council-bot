import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command, StateFilter

from bot.common.ai import generate_post, client
from bot.common.utils import generate_protocol, generate_attendance_list_full
from bot.keyboards.admin import admin_menu_kb, session_control_kb, admin_vote_kb, force_end_vote_kb
from random import randint
from bot.keyboards.common import vote_kb, common_kb

from config import OPTION

if str(OPTION) == 'MySQL':
    from bot.database.database import Database
else:
    from bot.database.database_postgres import Database

admin_router = Router()

class AdminStates(StatesGroup):
    session_name = State()
    session_password = State()
    admin_name = State()
    session_agenda = State()
    agenda_question = State()


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
    logging.info(f"Отримано ім'я сесії: {session_name}")
    await state.update_data(session_name=session_name)
    await message.answer("Введіть пароль для сесії:")
    await state.set_state(AdminStates.session_password)


@admin_router.message(AdminStates.session_password)
async def set_session_password(message: types.Message, state: FSMContext, db: Database):
    session_password = message.text.strip()
    logging.info(f"Отримано пароль сесії: {session_password}")
    await state.update_data(session_password=session_password)

    # Генеруємо унікальний код сесії
    session_code = randint(100000, 999999)
    session_data = await state.get_data()
    logging.info(f"Генеруємо код сесії: {session_code}")

    # Зберігаємо сесію в базі даних
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
    ignored_texts = ["🔄 Змінити порядок денний", "✅ Почати голосування по питаннях плану", "❌ Завершити сесію"]

    # Перевіряємо, чи текст є текстом кнопки
    if message.text in ignored_texts:
        await message.answer("Будь ласка, введіть новий порядок денний, а не натискайте кнопки.")
        return
    print(session_data)
    # Перевіряємо, чи є session_name і session_code у стані
    session_name = session_data.get('session_name')
    session_code = session_data.get('session_code')

    if not session_name or not session_code:
        await message.answer("Помилка: сесія не знайдена. Будь ласка, почніть з початку.")
        logging.error("Сесія не знайдена у стані")
        return

    # Обробляємо введений текст, видаляючи номери перед крапкою
    raw_agenda = message.text.splitlines()
    agenda = [line.split('.', 1)[1].strip() if '.' in line else line.strip() for line in raw_agenda]
    logging.info(f"Отримано новий порядок денний для сесії {session_name}: {agenda}")

    # Зберігаємо його в базу даних
    await db.set_session_agenda(session_code=session_code, agenda=agenda)

    # Форматуємо порядок денний для копіювання
    agenda_html = "<b>Порядок денний:</b>\n" + "\n".join(
        [f"{i + 1}. {item}" for i, item in enumerate(agenda)]
    )

    await message.answer(
        f"Порядок денний оновлено.\n\n{agenda_html}\n\nДалі ви можете:",
        reply_markup=session_control_kb(),
        parse_mode="HTML"
    )
    logging.info(f"Порядок денний збережено для сесії {session_name}")
    await state.clear()
    await state.update_data(session_code=session_code, session_name=session_name)


@admin_router.message(F.text == "🔄 Змінити порядок денний")
async def change_agenda(message: types.Message, state: FSMContext):
    session_data = await state.get_data()

    session_name = session_data.get('session_name')
    session_code = session_data.get('session_code')

    if not session_name or not session_code:
        print(session_data)
        await message.answer("Помилка: сесія не знайдена. Будь ласка, створіть нову сесію.")
        logging.error("Сесія не знайдена у стані")
        return

    logging.info(f"Користувач змінює порядок денний для сесії {session_name}")
    await message.answer("Введіть новий порядок денний (кожен пункт з нового рядка):")
    await state.set_state(AdminStates.session_agenda)


@admin_router.message(F.text == "✅ Почати голосування по питаннях плану")
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



@admin_router.message(StateFilter("voting"))
@admin_router.message(F.text.in_({"За", "Проти", "Утримаюсь"}))
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
    agenda = await db.get_session_agenda(session_code)
    current_question_index = await db.get_current_question_index(session_code)

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
            text=f"Оберіть наступну дію:",
            reply_markup=admin_vote_kb()
        )

        await db.set_current_question_index(session_code, current_question_index + 1)
        await state.set_state("admin_control")
    else:
        if message.from_user.id == admin_id:
            await message.answer(
                "Не всі проголосували. Ви можете дочекатися або завершити голосування вручну.",
                reply_markup=force_end_vote_kb()
            )


@admin_router.message(StateFilter("voting"))
@admin_router.message(F.text == "Завершити опитування по поточному питанню")
async def force_end_vote(message: types.Message, state: FSMContext, db: Database):
    session_data = await state.get_data()

    session_code = session_data.get("session_code")
    current_question_index = session_data.get("current_question_index", 0)
    agenda = session_data.get("agenda", [])

    if not session_code or current_question_index is None or not agenda:
        await message.answer("Помилка: сесія або питання не знайдені.")
        return

    current_question = agenda[current_question_index]

    admin_id = await db.get_admin_id(session_code)

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
        text=f"Оберіть наступну дію:",
        reply_markup=admin_vote_kb()
    )
    await db.set_current_question_index(session_code, current_question_index + 1)
    await state.set_state("admin_control")


@admin_router.message(StateFilter("voting"))
@admin_router.message(F.text == "Голосувати за наступне питання")
async def next_question(message: types.Message, state: FSMContext, db: Database):
    session_data = await state.get_data()

    session_code = session_data.get("session_code")
    current_question_index = session_data.get("current_question_index", 0)
    agenda = session_data.get("agenda", [])

    if current_question_index + 1 >= len(agenda):
        await message.answer(
            "Усі питання розглянуті. Ви можете завершити сесію.",
            reply_markup=admin_vote_kb()
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


from aiogram.types import FSInputFile

@admin_router.message(F.text == "❌ Завершити сесію")
async def end_session(message: types.Message, state: FSMContext, db: Database):
    session_data = await state.get_data()
    session_name = session_data.get('session_name')

    session_code = session_data.get("session_code")
    if not session_code:
        await message.answer("Помилка: сесія не знайдена.")
        return

    # Завершуємо сесію та отримуємо результати
    results = await db.end_session(session_code)

    total_participants = await db.count_of_participants(session_code)
    # Форматуємо результати
    results_text = "\n".join([
        f"<b>{index + 1}. {question}</b>\nЗа: {votes['for']}, Проти: {votes['against']}, Утримались: {votes['abstain']}, Не голосували: {votes['not_voted']}\nЦе рішення було <b>{'Прийнято' if votes['for'] * 2 > total_participants else 'Не прийнято'}</b>"
        for index, (question, votes) in enumerate(results.items())
    ])

    try:
        # Генеруємо документи
        protocol_path = await generate_protocol(session_code, db)
        attendance_list_path = await generate_attendance_list_full(session_code, session_name, db)

        protocol_file = FSInputFile(protocol_path)
        await message.answer_document(
            document=protocol_file
        )

        # Відправляємо список присутніх
        attendance_file = FSInputFile(attendance_list_path)
        await message.answer_document(
            document=attendance_file
        )

    except Exception as e:
        logging.error(f"Помилка під час генерації документів: {e}")
        await message.answer(f"Сталася помилка під час генерації документів: {str(e)}")

    # Надсилаємо результати голосування
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
async def send_generated_post(message: types.Message, state: FSMContext, db: Database):
    text = message.text
    logging.info(f"Згенеровано {text}")

    await message.reply("Генерую пост, зачекайте...")

    post = await generate_post(client, text)
    print(post)

    if post:
        await message.reply(f"{post}")
    else:
        await message.reply("На жаль, не вдалося згенерувати пост. Спробуйте пізніше.")

    await state.clear()