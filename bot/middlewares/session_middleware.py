from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import Message

class SessionMiddleware(BaseMiddleware):
    def __init__(self, db):
        self.db = db
        super().__init__()

    async def on_pre_process_message(self, message: Message, data: dict):
        session_code = data.get("session_code")
        if session_code and not self.db.get_session(session_code):
            await message.answer("Сесія не знайдена або завершена.")
            return False
        return True
