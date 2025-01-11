import logging
import asyncio
from multiprocessing import Process

from aiogram.client.default import DefaultBotProperties
from flask import Flask, request, jsonify
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from bot.common.commands import set_bot_commands, reset_bot_commands
from bot.database.database import Database, Base, DatabaseMiddleware
from bot.handlers.admin import admin_router
from bot.handlers.common import common_router
from bot.handlers.participant import participant_router
from config import TELEGRAM_TOKEN, DATABASE_URL, POSTGRESQL

# Налаштування логів
logging.basicConfig(level=logging.INFO)

# Ініціалізація Flask-сервера
app = Flask(__name__)

@app.route("/")
def index():
    return "Flask-сервер працює. Бот запущено!"

@app.route("/params", methods=["GET"])
def get_params():
    """Обробляє GET запити й повертає передані параметри."""
    params = request.args
    return jsonify({"parameters": params})

# Вибір бази даних
choose = 'Postgres'
if choose == 'MySQL':
    DATABASE = DATABASE_URL
else:
    DATABASE = f"postgresql+asyncpg{POSTGRESQL}"

# Ініціалізація SQLAlchemy
engine = create_async_engine(DATABASE, future=True, echo=True)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Інтеграція бази даних
db = Database(session_factory=async_session)

# Ініціалізація Telegram-бота
bot = Bot(
    token=TELEGRAM_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

dp.message.middleware(DatabaseMiddleware(db))

# Реєстрація роутерів
dp.include_router(admin_router)
dp.include_router(common_router)
dp.include_router(participant_router)

# Створення таблиць
async def create_tables():
    """Створює таблиці у базі даних."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logging.info("Таблиці створено.")

# Запуск Telegram-бота
async def run_bot():
    """Запускає Telegram-бота."""
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Встановлення команд для бота...")
    await set_bot_commands(bot)
    logging.info("Telegram-бот запущено.")
    await dp.start_polling(bot)

# Окремі функції для запуску процесів
def start_bot():
    """Функція для запуску Telegram-бота в окремому процесі."""
    asyncio.run(run_bot())

def start_flask():
    """Функція для запуску Flask-сервера."""
    app.run(host="0.0.0.0", port=5000, debug=False)

# Головна функція
if __name__ == "__main__":
    # Створення таблиць у базі даних
    asyncio.run(create_tables())

    # Запуск Flask і Telegram-бота у паралельних процесах
    bot_process = Process(target=start_bot)
    flask_process = Process(target=start_flask)

    bot_process.start()
    flask_process.start()

    bot_process.join()
    flask_process.join()
