import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command, StateFilter
from bot.keyboards.admin import admin_menu_kb, session_control_kb, vote_kb, admin_vote_kb, force_end_vote_kb
from bot.database.database import Database
from random import randint

admin_router = Router()

class AdminStates(StatesGroup):
    session_name = State()
    session_password = State()
    session_agenda = State()
    agenda_question = State()


@admin_router.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    logging.info("Хендлер /start викликано")
    await state.clear()
    await message.answer(
        "Привіт! Ви можете створити сесію або приєднатися до існуючої.",
        reply_markup=admin_menu_kb()
    )


@admin_router.message(F.text == "Створити сесію")
async def create_session(message: types.Message, state: FSMContext):
    logging.info("Користувач починає створення сесії")
    await message.answer("Введіть ім'я сесії:")
    await state.set_state(AdminStates.session_name)


@admin_router.message(AdminStates.session_name)
async def set_session_name(message: types.Message, state: FSMContext):
    session_name = message.text
    logging.info(f"Отримано ім'я сесії: {session_name}")
    await state.update_data(session_name=session_name)
    await message.answer("Введіть пароль для сесії:")
    await state.set_state(AdminStates.session_password)


@admin_router.message(AdminStates.session_password)
async def set_session_password(message: types.Message, state: FSMContext, db: Database):
    session_password = message.text
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

    # Додаємо session_code до стану
    await state.update_data(session_code=session_code)

    logging.info(f"Сесія створена: {session_data['session_name']} з кодом {session_code}")
    await message.answer(
        f"Сесія створена! \nКод сесії: <code>{session_code}</code>\nПароль: <code>{session_password}</code>",
        parse_mode="HTML"
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
    await message.answer(
        f"Перше питання для голосування:\n1. <b>{current_question}</b>",
        parse_mode="HTML",
        reply_markup=vote_kb()
    )
    await state.set_state("voting")


@admin_router.message(StateFilter("voting"))
@admin_router.message(F.text.in_({"За", "Проти", "Утримався"}))
async def collect_votes(message: types.Message, state: FSMContext, db: Database):
    session_data = await state.get_data()

    session_code = session_data.get("session_code")
    current_question_index = session_data.get("current_question_index", 0)
    agenda = session_data.get("agenda", [])

    if not session_code or current_question_index is None or not agenda:
        await message.answer("Помилка: сесія або питання не знайдені.")
        return

    # Зберігаємо голос
    await db.add_vote(
        session_code=session_code,
        user_id=message.from_user.id,
        question=agenda[current_question_index],
        vote=message.text
    )
    await message.answer("Ваш голос зараховано.")

    # Перевіряємо, чи всі проголосували
    all_votes_collected = await db.check_all_votes_collected(session_code, agenda[current_question_index])
    if all_votes_collected:
        # Відправляємо результати адміністратору
        vote_results = await db.get_vote_results(session_code, agenda[current_question_index])
        results_text = "\n".join(
            [f"<b>{key}</b>: {value}" for key, value in vote_results.items()]
        )

        await message.answer(
            f"Голосування завершено для питання:\n<b>{current_question_index + 1}. {agenda[current_question_index]}</b>\n\nРезультати:\n{results_text}",
            parse_mode="HTML",
            reply_markup=admin_vote_kb()  # Змінюємо клавіатуру для адміністратора
        )
        await state.set_state("admin_control")  # Переключаємо стан для адміністратора
    else:
        # Пропонуємо адміністратору завершити голосування
        if message.from_user.id == session_data.get("admin_id"):  # Якщо це адмін
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

    # Отримуємо результати голосування
    vote_results = await db.get_vote_results(session_code, agenda[current_question_index])
    results_text = "\n".join(
        [f"<b>{key}</b>: {value}" for key, value in vote_results.items()]
    )

    # Відправляємо результати адміністратору
    await message.answer(
        f"Голосування завершено для питання:\n<b>{current_question_index + 1}. {agenda[current_question_index]}</b>\n\nРезультати:\n{results_text}",
        parse_mode="HTML",
        reply_markup=admin_vote_kb()  # Змінюємо клавіатуру для адміністратора
    )
    await state.set_state("admin_control")  # Переключаємо стан для адміністратора



@admin_router.message(StateFilter("voting"))
@admin_router.message(F.text.in_({"Голосувати за наступне питання"}))
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
    next_question = agenda[next_question_index]

    await state.update_data(current_question_index=next_question_index)
    await message.answer(
        f"Наступне питання для голосування:\n<b>{next_question_index + 1}. {next_question}</b>",
        parse_mode="HTML",
        reply_markup=vote_kb()
    )


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

    # Форматуємо результати
    results_text = "\n".join([
        f"<b>{index + 1}. {question}</b>\nЗа: {votes['for']}, Проти: {votes['against']}, Утримались: {votes['abstain']}"
        for index, (question, votes) in enumerate(results.items())
    ])

    await message.answer(
        f"Сесію <b>{session_name}</b> завершено. \nРезультати голосування:\n\n{results_text}",
        parse_mode="HTML", reply_markup=admin_menu_kb()
    )
    await state.clear()
