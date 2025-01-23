import logging

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import StateFilter
from aiogram.filters import Command

from bot.keyboards.admin import admin_menu_kb, force_end_vote_kb
from bot.keyboards.participant import participant_menu_kb

from config import OPTION

if str(OPTION) == 'MySQL':
    from bot.database.database import Database
else:
    from bot.database.database_postgres import Database

participant_router = Router()

class ParticipantStates:
    entering_session_code = "entering_session_code"
    entering_session_password = "entering_session_password"
    entering_name = "entering_name"
    voting = "voting"

@participant_router.message(Command("join"))
@participant_router.message(F.text == "Приєднатися до сесії")
async def join_session(message: types.Message, state: FSMContext):
    """
    Учасник починає процес приєднання до сесії.
    """
    logging.info(f"Приєднання до сесії, користувач {message.from_user.id}")
    await state.set_state(ParticipantStates.entering_session_code)
    await message.answer("Введіть код сесії:")

@participant_router.message(StateFilter(ParticipantStates.entering_session_code))
async def handle_session_code(message: types.Message, state: FSMContext, db: Database):
    """
    Учасник вводить код сесії.
    """
    session_code = message.text.strip()
    session = await db.get_session_by_code(session_code)

    if not session:
        await message.answer("Сесія з таким кодом не знайдена. Спробуйте ще раз.")
        return

    logging.info(f"Користувач {message.from_user.id} заходить до сесії {session_code}")
    await state.update_data(session_code=session_code)
    await state.set_state(ParticipantStates.entering_session_password)
    await message.answer("Введіть пароль сесії:")

@participant_router.message(StateFilter(ParticipantStates.entering_session_password))
async def handle_session_password(message: types.Message, state: FSMContext, db: Database):
    """
    Учасник вводить пароль сесії.
    """
    data = await state.get_data()
    session_code = data.get("session_code")
    session = await db.get_session_by_code(session_code)

    if not session or session.password != message.text.strip():
        await message.answer("Неправильний пароль. Спробуйте ще раз.")
        return

    logging.info(f"Користувач {message.from_user.id} успішно приєднався до сесії {session_code}")
    await state.set_state(ParticipantStates.entering_name)
    await message.answer("Введіть своє ім'я:")

@participant_router.message(StateFilter(ParticipantStates.entering_name))
async def handle_name(message: types.Message, state: FSMContext, db: Database):
    """
    Учасник вводить своє ім'я.
    """
    user_name = message.text.strip()
    data = await state.get_data()
    session_code = data.get("session_code")

    # Додаємо учасника до сесії з ім'ям
    await db.add_participant(session_code=session_code, user_id=message.from_user.id, user_name=user_name)

    # Зберігаємо session_code, session_name та user_name
    session = await db.get_session_by_code(session_code)

    await state.set_state("voting")
    await state.update_data(session_code=session.code, session_name=session.name, user_name=user_name)

    await message.answer(
        f"Ви успішно приєдналися до сесії <b>{session.name}</b> як <b>{user_name}</b>!",
        parse_mode="HTML",
        reply_markup=participant_menu_kb()
    )

@participant_router.message(StateFilter("voting"), F.text.in_({"За", "Проти", "Утримаюсь"}))
async def collect_votes(message: types.Message, state: FSMContext, db: Database):
    session_data = await state.get_data()

    print('user_participant')

    # Отримуємо session_code
    session_code = session_data.get("session_code")
    if not session_code:
        await message.answer("Помилка: Сесія не знайдена.")
        return

    # Отримуємо поточне питання та порядок денний із бази даних
    current_question_index = session_data.get("current_question_index", 0)
    agenda = session_data.get("agenda", [])

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
            text=f"Введіть Прізвище та Ім'я людини, яка запропонувала це питання:",
            reply_markup=types.ReplyKeyboardRemove()
        )

    else:
        if message.from_user.id == admin_id:
            await message.answer(
                "Не всі проголосували. Ви можете дочекатися або завершити голосування вручну.",
                reply_markup=force_end_vote_kb()
            )


@participant_router.message(Command("info"))
@participant_router.message(F.text == "ℹ️ Інформація про сесію")
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


@participant_router.message(Command('leave'))
@participant_router.message(F.text == "🚪 Вийти з сесії")
async def leave_session(message: types.Message, state: FSMContext, db: Database):
    """
    Учасник залишає сесію.
    """
    # Отримуємо дані стану
    session_data = await state.get_data()
    session_code = session_data.get("session_code")
    session_name = session_data.get("session_name")
    user_id = message.from_user.id

    if not session_code:
        await message.answer("Помилка: Ви не перебуваєте в жодній сесії.")
        return

    admin_id = await db.get_admin_id(session_code)
    if user_id == admin_id:
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

    else:
        # Видаляємо учасника з бази даних
        try:
            await db.remove_participant(session_code=session_code, user_id=user_id)
            await state.clear()
            await message.answer(
                f"Ви успішно вийшли із сесії <b>{session_name}</b> (код: {session_code}).",
                reply_markup=types.ReplyKeyboardRemove()
            )
        except Exception as e:
            logging.error(f"Помилка при спробі залишити сесію: {e}")
            await message.answer("Виникла помилка при спробі залишити сесію. Спробуйте ще раз.")
