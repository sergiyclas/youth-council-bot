import logging
from multiprocessing import Process
from aiogram import Bot, Dispatcher
from flask import Flask, jsonify, request
from aiogram.fsm.storage.memory import MemoryStorage
from config import TELEGRAM_TOKEN
import asyncio

app = Flask(__name__)

bot = Bot(token=TELEGRAM_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

logging.basicConfig(level=logging.INFO)

register_routes(app, bot, dp)

@app.route('/')
def index():
    """Головна сторінка для перевірки статусу сервера."""
    status = "Бот запущений."
    return f"Сервер Flask працює. Статус бота: {status}"

@app.route('/params', methods=['GET'])
def get_params():
    """Повернення переданих параметрів."""
    query_params = request.args
    return jsonify({"parameters": query_params})

async def start_bot():
    """Запуск Telegram-бота."""
    logging.info("Запуск Telegram-бота.")
    await dp.start_polling(bot, skip_updates=True)

def run_bot():
    """Функція для запуску Telegram-бота в окремому процесі."""
    asyncio.run(start_bot())

def run_flask():
    """Функція для запуску Flask-сервера."""
    app.run(host="0.0.0.0", port=5000, debug=False)

if __name__ == "__main__":
    bot_process = Process(target=run_bot)
    flask_process = Process(target=run_flask)

    bot_process.start()
    flask_process.start()

    bot_process.join()
    flask_process.join()
