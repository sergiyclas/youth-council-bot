import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot.database.database import Database
from bot.handlers.admin import register_admin_handlers
from bot.handlers.participant import register_participant_handlers
from bot.handlers.common import register_common_handlers
from config import TELEGRAM_TOKEN

# Ініціалізація бота та диспетчера
logging.basicConfig(level=logging.INFO)
bot = Bot(token=TELEGRAM_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
db = Database()

# Реєстрація хендлерів
register_admin_handlers(dp, db)
register_participant_handlers(dp, db)
register_common_handlers(dp)

# Запуск бота
async def main():
    logging.info("Бот запущено!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
