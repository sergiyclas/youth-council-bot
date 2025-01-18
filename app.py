import logging
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
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
import asyncpg

# Налаштування логів
logging.basicConfig(level=logging.INFO)

# Ініціалізація бази даних
choose = 'postgre'
if choose == 'MySQL':
    DATABASE = DATABASE_URL
else:
    DATABASE = "postgresql+asyncpg" + str(POSTGRESQL)

engine = create_async_engine(DATABASE, future=True)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
db = Database(session_factory=async_session)

# Ініціалізація Telegram-бота
bot = Bot(
    token=TELEGRAM_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
dp.message.middleware(DatabaseMiddleware(db))

dp.include_router(admin_router)
dp.include_router(common_router)
dp.include_router(participant_router)

async def create_tables():
    """Створює таблиці у базі даних."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logging.info("Таблиці створено.")

async def run_bot():
    """Запускає Telegram-бота."""
    await bot.delete_webhook(drop_pending_updates=True)  # Скидання закинутих повідомлень
    logging.info("Встановлення команд для бота...")
    await set_bot_commands(bot)  # Встановлюємо команди
    logging.info("Команди встановлено. Telegram-бот запущено.")
    await dp.start_polling(bot)

def main():
    """Основна функція для запуску бота та створення БД в одному подієвому циклі."""
    loop = asyncio.get_event_loop()
    loop.run_until_complete(create_tables())
    loop.run_until_complete(run_bot())

if __name__ == "__main__":
    main()
