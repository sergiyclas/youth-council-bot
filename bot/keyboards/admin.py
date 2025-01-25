from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

def admin_menu_kb():
    """Клавіатура для вибору дій адміністратором."""
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(
        KeyboardButton(text="Створити сесію"),
        KeyboardButton(text="Приєднатися до сесії")
    )
    return keyboard.adjust(2).as_markup(resize_keyboard=True)

def session_control_resized_kb():
    """Клавіатура для керування сесією."""
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(
        KeyboardButton(text="🔄 Змінити порядок денний"),
        KeyboardButton(text="✅ Почати голосування по питаннях порядку денного"),
        KeyboardButton(text="⚙️ Налаштувати інформацію про МР"),
        KeyboardButton(text="ℹ️ Інформація про сесію"),
        KeyboardButton(text="❌ Завершити сесію")
    )
    return keyboard.adjust(1).as_markup(resize_keyboard=True)


def session_control_kb():
    """Клавіатура для керування сесією."""
    keyboard = ReplyKeyboardBuilder()

    # Додаємо кнопки по команді
    keyboard.add(
        KeyboardButton(text="✅ Почати голосування по питаннях порядку денного"),
    )

    keyboard.row(
        KeyboardButton(text="🔄 Змінити порядок денний"),
        KeyboardButton(text="⚙️ Налаштувати інформацію про МР"),
    )

    keyboard.row(
        KeyboardButton(text="ℹ️ Інформація про сесію"),
        KeyboardButton(text="❌ Завершити сесію")
    )

    # Повертаємо клавіатуру
    return keyboard.as_markup(resize_keyboard=True)


def yes_no_kb():
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(
        KeyboardButton(text="Так"),
        KeyboardButton(text="Ні"),
    )
    return keyboard.adjust(1).as_markup(resize_keyboard=True)

def vote_kb():
    """Клавіатура для голосування."""
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(
        KeyboardButton(text="За"),
        KeyboardButton(text="Проти"),
        KeyboardButton(text="Утримаюсь")
    )
    return keyboard.adjust(1).as_markup(resize_keyboard=True)

def force_end_vote_kb():
    """Клавіатура для примусового завершення голосування."""
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(
        KeyboardButton(text="Завершити опитування по поточному питанню")
    )
    return keyboard.as_markup(resize_keyboard=True)


def admin_vote_kb():
    """Клавіатура для управління після голосування."""
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(
        KeyboardButton(text="Голосувати за наступне питання"),
        KeyboardButton(text="❌ Завершити сесію")
    )
    return keyboard.adjust(1).as_markup(resize_keyboard=True)

def admin_end_vote_kb():
    """Клавіатура для управління після голосування."""
    keyboard = ReplyKeyboardBuilder()

    keyboard.row(
        KeyboardButton(text="⚙️ Налаштувати інформацію про МР"),
        KeyboardButton(text="📝 Заповнити родові відмінки імен")
    )

    keyboard.add(
        KeyboardButton(text="❌ Завершити сесію"),
    )
    return keyboard.adjust(1).as_markup(resize_keyboard=True)


def back_kb():
    """Клавіатура з кнопкою назад."""
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text="Назад"))
    return keyboard.as_markup(resize_keyboard=True)


def set_rv_name():
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(
        KeyboardButton(text="Пропустити"),
    )
    return keyboard.adjust(1).as_markup(resize_keyboard=True)

def set_session_type_kb():
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(
            KeyboardButton(text="Чергового"),
            KeyboardButton(text="Позачергового"),
    )

    return keyboard.adjust(1).as_markup(resize_keyboard=True)

def admin_fea_kb():
    keyboard = ReplyKeyboardBuilder()

    keyboard.row(
        KeyboardButton(text="/show_recent"),
        KeyboardButton(text="/upload_session")
    )

    keyboard.row(
        KeyboardButton(text="/info_user"),
        KeyboardButton(text="/id_all_users")
    )

    keyboard.add(
        KeyboardButton(text="/exit_admin"),
    )
    return keyboard.adjust(2).as_markup(resize_keyboard=True)