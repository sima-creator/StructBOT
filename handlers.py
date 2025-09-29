import logging
import re
from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_ID, user_selections, active_users, admin_states, SUBJECTS_TOPICS
from keyboards import (
    main_keyboard, subjects_keyboard, topics_keyboard,
    admin_panel_keyboard, admin_cancel_keyboard, admin_users_keyboard
)
from services import notify_admin, handle_admin_broadcast, handle_admin_reply, send_message_to_user

logger = logging.getLogger(__name__)


async def send_message_with_notify(update, context, text, user_message=None):
    """Отправляет сообщение пользователю и уведомляет админа"""
    user = update.effective_user

    # Определяем правильную клавиатуру
    if user.id == ADMIN_ID and admin_states.get(user.id) == 'admin_panel':
        reply_markup = admin_panel_keyboard()
    else:
        reply_markup = main_keyboard()

    # Отправляем сообщение пользователю
    await update.message.reply_text(text, reply_markup=reply_markup)

    # Уведомляем админа (БЕЗ Markdown) - кроме самого админа
    if user.id != ADMIN_ID:
        await notify_admin(context.application, user, text, user_message)


# ==================== ОСНОВНЫЕ КОМАНДЫ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"Пользователь {user.id} запустил бота")

    if user.id in user_selections:
        del user_selections[user.id]

    welcome_text = f"""Привет, {user.first_name}! 👋

Мы — команда экспертов с огромным опытом в сфере строительных дисциплин. Наша специализация — выполнение курсовых работ высочайшего качества с полным сопровождением на всех этапах.

Важным преимуществом нашего сервиса является персональный эксперт, который закрепляется за вами при выборе соответствующего тарифа. Ваш специалист будет на связи 24/7, чтобы оперативно отвечать на вопросы, вносить правки по требованию преподавателя и сопровождать вас вплоть до успешной сдачи работы.

Каждый проект выполняется профильным мастером, что гарантирует глубокое погружение в тему. Мы настолько уверены в качестве, что гарантируем высший балл.

Выбери нужный раздел:"""

    await send_message_with_notify(update, context, welcome_text, "/start")


async def handle_subjects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📚 Доступные предметы:\n\nВыбери предмет для заказа курсовой работы:"
    await update.message.reply_text(text, reply_markup=subjects_keyboard())


async def handle_subject_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, subject: str):
    user = update.effective_user
    user_selections[user.id] = {'subject': subject}

    text = f"""🎯 Выбран предмет: {subject}

📝 Доступные темы:

Выбери подходящую тему или укажи свою:"""

    await update.message.reply_text(text, reply_markup=topics_keyboard(subject))


async def handle_topic_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, topic: str):
    user = update.effective_user

    if user.id in user_selections:
        subject = user_selections[user.id]['subject']
        user_selections[user.id]['topic'] = topic

        if topic == "Другая тема (уточнить)":
            text = f"""✏️ Выбрана своя тема

Предмет: {subject}

Напиши свою тему курсовой работы:"""
            await send_message_with_notify(update, context, text, f"Своя тема для {subject}")
        else:
            text = f"""✅ Тема выбрана!

📚 Предмет: {subject}
📝 Тема: {topic}

💰 Стоимость: 2500 руб.
⏰ Срок выполнения: 7 дней

🛒 Для оформления заказа нажми '🛒 Корзина'"""
            await send_message_with_notify(update, context, text, f"Тема: {topic} для {subject}")


async def handle_custom_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    custom_topic = update.message.text

    if user.id in user_selections and 'subject' in user_selections[user.id]:
        subject = user_selections[user.id]['subject']
        user_selections[user.id]['topic'] = custom_topic

        text = f"""✅ Ваша тема принята!

📚 Предмет: {subject}
📝 Тема: {custom_topic}

💰 Стоимость: 3000 руб. (индивидуальная тема)
⏰ Срок выполнения: 10 дней

🛒 Для оформления заказа нажми '🛒 Корзина'"""

        await send_message_with_notify(update, context, text, f"Своя тема: {custom_topic} для {subject}")
    else:
        await send_message_with_notify(update, context, "Сначала выбери предмет 👆")


async def clear_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if user.id in user_selections:
        del user_selections[user.id]

    await send_message_with_notify(update, context, "🧹 Чат полностью очищен!\n\nВсе выборы сброшены.", "Очистка чата")


# ==================== АДМИН ФУНКЦИИ ====================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Активация админ-панели"""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return

    admin_states[user.id] = 'admin_panel'
    await update.message.reply_text("🛠️ Панель администратора", reply_markup=admin_panel_keyboard())


async def handle_admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопок админ-панели"""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return

    text = update.message.text

    if text == '👥 Пользователи':
        await admin_users(update, context)
    elif text == '📊 Статистика':
        await admin_stats(update, context)
    elif text == '📢 Общая рассылка':
        admin_states[user.id] = 'awaiting_broadcast'
        await update.message.reply_text(
            "📢 Введите текст для рассылки всем пользователям:",
            reply_markup=admin_cancel_keyboard()
        )
    elif text == '🚪 Обычный режим':
        admin_states.pop(user.id, None)
        await update.message.reply_text("Вы перешли в обычный режим", reply_markup=main_keyboard())
    elif text == '↩️ Назад в админ-панель':
        admin_states[user.id] = 'admin_panel'
        await update.message.reply_text("Возврат в админ-панель", reply_markup=admin_panel_keyboard())
    elif text == '❌ Отмена':
        admin_states[user.id] = 'admin_panel'
        await update.message.reply_text("Действие отменено", reply_markup=admin_panel_keyboard())


async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список пользователей с кнопками для ответа"""
    if not active_users:
        await update.message.reply_text("📭 Нет активных пользователей", reply_markup=admin_panel_keyboard())
        return

    users_text = "👥 Активные пользователи:\n\n"
    for user_id, user_info in active_users.items():
        users_text += f"👤 {user_info.get('first_name', 'Неизвестный')}\n"
        users_text += f"🆔 ID: {user_id}\n"
        if user_info.get('username'):
            users_text += f"📱 @{user_info['username']}\n"
        users_text += f"📝 {user_info.get('last_activity', 'Нет данных')}\n"
        users_text += "━━━━━━━━━━━━━━━━━━━━\n"

    users_text += f"\n💡 Всего: {len(active_users)} пользователей"
    users_text += f"\n\n💬 Нажмите на кнопку ниже чтобы ответить пользователю"

    await update.message.reply_text(users_text, reply_markup=admin_users_keyboard())


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика бота"""
    stats_text = f"""📊 Статистика бота

👥 Активных пользователей: {len(active_users)}
📝 Текущих заказов: {len(user_selections)}"""

    await update.message.reply_text(stats_text, reply_markup=admin_panel_keyboard())


async def admin_reply_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /reply ID текст"""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text("❌ Формат: /reply ID ваш_текст\n\nПример: /reply 123456789 Привет! Как дела?")
        return

    try:
        target_user_id = int(context.args[0])
        reply_text = ' '.join(context.args[1:])

        success = await send_message_to_user(context, target_user_id, reply_text)

        if success:
            target_user_info = active_users.get(target_user_id, {})
            user_name = target_user_info.get('first_name', 'Неизвестный пользователь')
            success_msg = f"✅ Ответ отправлен пользователю {user_name} (ID: {target_user_id})"
            await update.message.reply_text(success_msg, reply_markup=admin_panel_keyboard())
        else:
            await update.message.reply_text("❌ Ошибка отправки", reply_markup=admin_panel_keyboard())

    except ValueError:
        await update.message.reply_text("❌ Неправильный формат ID. ID должен состоять только из цифр.")
    except Exception as e:
        error_msg = f"❌ Ошибка отправки: {str(e)}"
        await update.message.reply_text(error_msg)


async def admin_reply_underscore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /reply_123456789 текст"""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return

    command_text = update.message.text

    try:
        parts = command_text.split('_', 1)
        if len(parts) < 2:
            await update.message.reply_text("❌ Формат: /reply_123456789 ваш_текст")
            return

        rest = parts[1].strip()
        if not rest:
            await update.message.reply_text("❌ Формат: /reply_123456789 ваш_текст")
            return

        space_index = rest.find(' ')
        if space_index == -1:
            await update.message.reply_text(
                "❌ Введите текст ответа после ID\n\nПример: /reply_123456789 Привет! Как дела?")
            return

        user_id_part = rest[:space_index]
        reply_text = rest[space_index:].strip()

        if not reply_text:
            await update.message.reply_text("❌ Введите текст ответа после ID")
            return

        target_user_id = int(user_id_part)
        success = await send_message_to_user(context, target_user_id, reply_text)

        if success:
            target_user_info = active_users.get(target_user_id, {})
            user_name = target_user_info.get('first_name', 'Неизвестный пользователь')
            success_msg = f"✅ Ответ отправлен пользователю {user_name} (ID: {target_user_id})"
            await update.message.reply_text(success_msg, reply_markup=admin_panel_keyboard())
        else:
            await update.message.reply_text("❌ Ошибка отправки", reply_markup=admin_panel_keyboard())

    except ValueError:
        await update.message.reply_text("❌ Неправильный формат ID. ID должен состоять только из цифр.")
    except Exception as e:
        error_msg = f"❌ Ошибка отправки: {str(e)}"
        await update.message.reply_text(error_msg)


# ==================== ОБРАБОТКА ИНЛАЙН-КНОПОК ====================
async def handle_inline_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на инлайн-кнопки"""
    from telegram.ext import CallbackQueryHandler
    query = update.callback_query
    await query.answer()

    user = query.from_user
    if user.id != ADMIN_ID:
        return

    callback_data = query.data

    if callback_data.startswith('quick_reply_'):
        try:
            user_id = int(callback_data.split('_')[2])
            if user_id in active_users:
                admin_states[user.id] = {'mode': 'awaiting_reply', 'target_id': user_id}
                user_info = active_users[user_id]

                await query.edit_message_text(
                    text=query.message.text + f"\n\n🔄 Режим ответа для {user_info['first_name']} активирован",
                    reply_markup=None
                )

                await context.bot.send_message(
                    chat_id=user.id,
                    text=f"💬 Введите текст ответа для пользователя {user_info['first_name']} (ID: {user_id}):",
                    reply_markup=admin_cancel_keyboard()
                )
            else:
                await context.bot.send_message(
                    chat_id=user.id,
                    text="❌ Пользователь не найден",
                    reply_markup=admin_panel_keyboard()
                )
        except (ValueError, IndexError):
            await context.bot.send_message(
                chat_id=user.id,
                text="❌ Ошибка формата",
                reply_markup=admin_panel_keyboard()
            )


# ==================== ГЛАВНЫЙ ОБРАБОТЧИК СООБЩЕНИЙ ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text

    # Если админ в админ-панели - обрабатываем админские функции
    if user.id == ADMIN_ID and admin_states.get(user.id):
        state = admin_states.get(user.id)

        if state == 'awaiting_broadcast':
            await handle_admin_broadcast(update, context)
        elif isinstance(state, dict) and state.get('mode') == 'awaiting_reply':
            await handle_admin_reply(update, context)
        elif text.startswith('💬 Ответить'):
            try:
                match = re.search(r'ID: (\d+)\)', text)
                if match:
                    user_id = int(match.group(1))
                    if user_id in active_users:
                        admin_states[user.id] = {'mode': 'awaiting_reply', 'target_id': user_id}
                        user_info = active_users[user_id]
                        await update.message.reply_text(
                            f"💬 Введите текст ответа для пользователя {user_info['first_name']} (ID: {user_id}):",
                            reply_markup=admin_cancel_keyboard()
                        )
                    else:
                        await update.message.reply_text("❌ Пользователь не найден", reply_markup=admin_panel_keyboard())
                else:
                    await update.message.reply_text("❌ Ошибка формата", reply_markup=admin_panel_keyboard())
            except (ValueError, IndexError):
                await update.message.reply_text("❌ Ошибка формата", reply_markup=admin_panel_keyboard())
        else:
            await handle_admin_buttons(update, context)
        return

    # Обработка пользовательских сообщений
    if text == '📚 Предметы':
        await handle_subjects(update, context)
    elif text == 'ℹ️ Гарантии':
        await send_message_with_notify(update, context,
                                       "ℹ️ Наши гарантии:\n\n✅ Качество работ\n✅ Соблюдение сроков\n✅ Конфиденциальность",
                                       "Гарантии")
    elif text == '💰 Цены':
        await send_message_with_notify(update, context,
                                       "💰 Наши цены:\n\n📝 Курсовая: от 2000 руб.\n⚡ Срочный заказ: +50%\n📚 Сложный предмет: +30%",
                                       "Цены")
    elif text == '👨‍🎓 О нас':
        await send_message_with_notify(update, context,
                                       "👨‍🎓 Профессиональная команда авторов с опытом работы более 5 лет!", "О нас")
    elif text == '🛒 Корзина':
        if user.id in user_selections and 'topic' in user_selections[user.id]:
            selection = user_selections[user.id]
            await send_message_with_notify(update, context,
                                           f"🛒 Твой заказ:\n\nПредмет: {selection['subject']}\nТема: {selection['topic']}\nСтоимость: 2500 руб.\n\n💳 Раздел оплаты в разработке...",
                                           "Корзина")
        else:
            await send_message_with_notify(update, context, "🛒 Корзина пуста. Сначала выбери тему работы!",
                                           "Корзина пуста")
    elif text == '📞 Контакты':
        await send_message_with_notify(update, context,
                                       "📞 Наши контакты:\n\n👤 Менеджер: @manager\n📧 Email: info@example.com",
                                       "Контакты")
    elif text == '🧹 Очистить чат':
        await clear_chat(update, context)
    elif text in SUBJECTS_TOPICS.keys():
        await handle_subject_selection(update, context, text)
    elif text == '↩️ Назад в меню':
        await start(update, context)
    elif text == '↩️ К выбору предмета':
        await handle_subjects(update, context)
    elif text == '🏠 В главное меню':
        await start(update, context)
    elif any(text in topics for topics in SUBJECTS_TOPICS.values()):
        await handle_topic_selection(update, context, text)
    elif user.id in user_selections and 'subject' in user_selections[user.id] and 'topic' not in user_selections[
        user.id]:
        await handle_custom_topic(update, context)
    else:
        await send_message_with_notify(update, context, "Пожалуйста, используй кнопки меню 👆", text)