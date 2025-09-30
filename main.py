import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler

from config import BOT_TOKEN, ADMIN_ID
from handlers import (
    start, handle_message, handle_inline_buttons,
    admin_panel, admin_users, admin_stats, admin_reply_command, admin_reply_underscore,
    create_order_from_cart, handle_variant_input, handle_consultation, handle_cart, clear_chat
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    try:
        application = Application.builder().token(BOT_TOKEN).build()

        # ОБЯЗАТЕЛЬНО: Обработчик для ввода варианта ДОЛЖЕН БЫТЬ ПЕРВЫМ
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.Regex(r'^\d+$'),
            handle_variant_input
        ))

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
            filters.TEXT & filters.User(ADMIN_ID) & filters.Regex(r'^/reply_\d+'),
            admin_reply_underscore
        ))

        # Обработчик для оформления заказа
        application.add_handler(MessageHandler(
            filters.TEXT & filters.Regex(r'^✅ Оформить заказ$'),
            create_order_from_cart
        ))

        print("✅ Бот активен!")

        application.run_polling()

    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")

if __name__ == '__main__':
    main()