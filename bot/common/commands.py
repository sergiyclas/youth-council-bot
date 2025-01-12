from aiogram.types import BotCommand

async def set_bot_commands(bot):
    commands = [
        BotCommand(command="/start", description="Запустити/Обнулити бота"),
        BotCommand(command="/help", description="Отримати допомогу по командах"),
        BotCommand(command="/join", description="Приєднатися до сесії"),
        BotCommand(command="/create_session", description="Створити сесію"),
        BotCommand(command="/info", description="Інформація про сесію"),
        BotCommand(command="/post", description="Згенерувати пост(лише для адмінів)"),
        BotCommand(command="/leave", description="Залишити сесію"),
    ]
    await bot.set_my_commands(commands)

async def reset_bot_commands(bot):
    """Скидає всі команди бота."""
    await bot.delete_my_commands()


#
# from aiogram.types import BotCommandScopeChat
#
# # Команди для адміна
# admin_commands = [
#     BotCommand(command="/start", description="Запустити бота"),
#     BotCommand(command="/create", description="Створити сесію"),
#     BotCommand(command="/control", description="Керування сесією"),
# ]
#
# # Команди для учасника
# participant_commands = [
#     BotCommand(command="/join", description="Приєднатися до сесії"),
#     BotCommand(command="/info", description="Інформація про сесію"),
#     BotCommand(command="/leave", description="Залишити сесію"),
# ]
#
# # Встановлення різних команд
# await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
# await bot.set_my_commands(participant_commands, scope=BotCommandScopeChat(chat_id=participant_id))
