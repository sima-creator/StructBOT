import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_ID, active_users, admin_states
from keyboards import admin_panel_keyboard, admin_cancel_keyboard, quick_reply_inline_keyboard

logger = logging.getLogger(__name__)


async def notify_admin(application, user, message, user_message=None):
    """Отправляет уведомление админу с инлайн-кнопкой"""
    if user.id == ADMIN_ID:
        return

    try:
        # Сохраняем пользователя для возможного ответа
        active_users[user.id] = {
            'first_name': user.first_name,
            'username': user.username,
            'last_activity': user_message or message
        }

        # ФОРМИРУЕМ СООБЩЕНИЕ БЕЗ MARKDOWN - ПРОСТОЙ ТЕКСТ
        admin_message = "👤 Переписка с пользователем:\n\n"
        admin_message += f"🆔 ID: {user.id}\n"
        admin_message += f"👤 Имя: {user.first_name}\n"
        if user.username:
            admin_message += f"📱 @{user.username}\n"

        if user_message:
            admin_message += f"\n💬 Сообщение пользователя:\n{user_message}\n"

        admin_message += f"\n📨 Ответ бота:\n{message}"

        # ОТПРАВЛЯЕМ БЕЗ parse_mode - ПРОСТОЙ ТЕКСТ
        await application.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_message,
            reply_markup=quick_reply_inline_keyboard(user.id, user.first_name)
        )
    except Exception as e:
        logger.error(f"Ошибка отправки админу: {e}")


async def send_message_to_user(context, target_user_id, reply_text):
    """Отправляет сообщение пользователю"""
    try:
        await context.bot.send_message(
            chat_id=target_user_id,
            text=f"💬 Сообщение от поддержки:\n\n{reply_text}"
        )
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки пользователю {target_user_id}: {e}")
        return False


async def handle_admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка рассылки из админ-панели"""
    if update.message.text == '❌ Отмена':
        admin_states[update.effective_user.id] = 'admin_panel'
        await update.message.reply_text("Рассылка отменена", reply_markup=admin_panel_keyboard())
        return

    if not active_users:
        await update.message.reply_text("❌ Нет активных пользователей для рассылки",
                                        reply_markup=admin_panel_keyboard())
        return

    broadcast_text = update.message.text
    successful = 0
    failed = 0

    # Отправляем рассылку
    for user_id in active_users.keys():
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📢 Сообщение от поддержки:\n\n{broadcast_text}"
            )
            successful += 1
        except Exception as e:
            failed += 1
            logger.error(f"Ошибка рассылки пользователю {user_id}: {e}")

    admin_states[update.effective_user.id] = 'admin_panel'
    await update.message.reply_text(
        f"📢 Рассылка завершена:\n\n✅ Успешно: {successful}\n❌ Неудачно: {failed}",
        reply_markup=admin_panel_keyboard()
    )


async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ответа конкретному пользователю"""
    if update.message.text == '❌ Отмена':
        admin_states[update.effective_user.id] = 'admin_panel'
        await update.message.reply_text("Ответ отменен", reply_markup=admin_panel_keyboard())
        return

    state = admin_states.get(update.effective_user.id)
    if isinstance(state, dict) and state.get('mode') == 'awaiting_reply':
        target_id = state.get('target_id')
        reply_text = update.message.text

        success = await send_message_to_user(context, target_id, reply_text)

        if success:
            target_user_info = active_users.get(target_id, {})
            user_name = target_user_info.get('first_name', 'Неизвестный пользователь')
            admin_states[update.effective_user.id] = 'admin_panel'
            await update.message.reply_text(
                f"✅ Ответ отправлен пользователю {user_name} (ID: {target_id})",
                reply_markup=admin_panel_keyboard()
            )
        else:
            admin_states[update.effective_user.id] = 'admin_panel'
            await update.message.reply_text(
                f"❌ Ошибка отправки пользователю",
                reply_markup=admin_panel_keyboard()
            )