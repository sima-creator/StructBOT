import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler

from config import BOT_TOKEN
from handlers import (
    start, handle_message, handle_inline_buttons,
    admin_panel, admin_users, admin_stats, admin_reply_command, admin_reply_underscore
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    try:
        application = Application.builder().token(BOT_TOKEN).build()

        # Обработчики для пользователей
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        # Обработчик инлайн-кнопок
        application.add_handler(CallbackQueryHandler(handle_inline_buttons))

        # Команды админа
        application.add_handler(CommandHandler("admin", admin_panel))
        application.add_handler(CommandHandler("users", admin_users))
        application.add_handler(CommandHandler("stats", admin_stats))
        application.add_handler(CommandHandler("reply", admin_reply_command))

        # Обработчик для команд с подчеркиванием
        application.add_handler(MessageHandler(
            filters.TEXT & filters.User(user_id=7251427348) & filters.Regex(r'^/reply_\d+'),
            admin_reply_underscore
        ))

        logger.info("🤖 Бот запущен с новой структурой!")
        print("✅ Бот активен!")
        print("🔧 Структура: config.py, handlers.py, keyboards.py, services.py")
        print("💡 Все функции работают как и раньше!")

        application.run_polling()

    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")

if __name__ == '__main__':
    main()