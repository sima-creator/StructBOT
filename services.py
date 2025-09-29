import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_ID, PRICES
from database import db
from keyboards import quick_reply_inline_keyboard, admin_panel_keyboard, admin_cancel_keyboard

logger = logging.getLogger(__name__)


async def notify_admin(application, user, message, user_message=None):
    if user.id == ADMIN_ID:
        return

    try:
        db.save_user(user.id, user.first_name, user.username)
        db.save_user_activity(
            user_id=user.id,
            activity_type="user_message",
            message_text=user_message,
            bot_response=message
        )

        admin_message = "👤 Переписка с пользователем:\n\n"
        admin_message += f"🆔 ID: {user.id}\n"
        admin_message += f"👤 Имя: {user.first_name}\n"
        if user.username:
            admin_message += f"📱 @{user.username}\n"

        if user_message:
            admin_message += f"\n💬 Сообщение пользователя:\n{user_message}\n"

        admin_message += f"\n📨 Ответ бота:\n{message}"

        await application.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_message,
            reply_markup=quick_reply_inline_keyboard(user.id, user.first_name)
        )
    except Exception as e:
        logger.error(f"Ошибка отправки админу: {e}")


async def send_message_with_notify(update, context, text, user_message=None):
    user = update.effective_user

    from config import admin_states
    if user.id == ADMIN_ID and admin_states.get(user.id) == 'admin_panel':
        from keyboards import admin_panel_keyboard
        reply_markup = admin_panel_keyboard()
    else:
        from keyboards import main_keyboard
        reply_markup = main_keyboard()

    await update.message.reply_text(text, reply_markup=reply_markup)

    if user.id != ADMIN_ID:
        await notify_admin(context.application, user, text, user_message)


async def send_message_to_user(context, target_user_id, reply_text, update):
    try:
        await context.bot.send_message(
            chat_id=target_user_id,
            text=f"💬 Сообщение от поддержки:\n\n{reply_text}"
        )

        db.save_user_activity(
            user_id=target_user_id,
            activity_type="admin_reply",
            message_text=reply_text,
            bot_response="Ответ отправлен"
        )

        return True
    except Exception as e:
        logger.error(f"Ошибка отправки пользователю {target_user_id}: {e}")
        return False


async def handle_admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from config import admin_states, ADMIN_ID

    user = update.effective_user
    if user.id != ADMIN_ID:
        return

    if update.message.text == '❌ Отмена':
        admin_states[user.id] = 'admin_panel'
        await update.message.reply_text("Рассылка отменена", reply_markup=admin_panel_keyboard())
        return

    active_users = db.get_active_users(24)
    if not active_users:
        await update.message.reply_text("❌ Нет активных пользователей для рассылки",
                                        reply_markup=admin_panel_keyboard())
        return

    broadcast_text = update.message.text
    successful = 0
    failed = 0

    for user_id in active_users.keys():
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📢 Сообщение от поддержки:\n\n{broadcast_text}"
            )
            successful += 1

            db.save_user_activity(
                user_id=user_id,
                activity_type="broadcast",
                message_text=broadcast_text,
                bot_response="Рассылка"
            )
        except Exception as e:
            failed += 1
            logger.error(f"Ошибка рассылки пользователю {user_id}: {e}")

    admin_states[user.id] = 'admin_panel'
    await update.message.reply_text(
        f"📢 Рассылка завершена:\n\n✅ Успешно: {successful}\n❌ Неудачно: {failed}",
        reply_markup=admin_panel_keyboard()
    )


async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from config import admin_states, ADMIN_ID

    user = update.effective_user
    if user.id != ADMIN_ID:
        return

    if update.message.text == '❌ Отмена':
        admin_states[user.id] = 'admin_panel'
        await update.message.reply_text("Ответ отменен", reply_markup=admin_panel_keyboard())
        return

    state = admin_states.get(user.id)
    if isinstance(state, dict) and state.get('mode') == 'awaiting_reply':
        target_id = state.get('target_id')
        reply_text = update.message.text

        success = await send_message_to_user(context, target_id, reply_text, update)

        if success:
            active_users = db.get_active_users(1)
            target_user_info = active_users.get(target_id, {})
            user_name = target_user_info.get('first_name', 'Неизвестный пользователь')
            admin_states[user.id] = 'admin_panel'
            await update.message.reply_text(
                f"✅ Ответ отправлен пользователю {user_name} (ID: {target_id})",
                reply_markup=admin_panel_keyboard()
            )
        else:
            admin_states[user.id] = 'admin_panel'
            await update.message.reply_text(
                f"❌ Ошибка отправки пользователю",
                reply_markup=admin_panel_keyboard()
            )