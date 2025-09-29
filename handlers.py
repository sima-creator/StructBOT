import logging
import re
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from config import ADMIN_ID, SUBJECTS_TOPICS, PRICES, admin_states, ORDER_STATUSES
from database import db
from keyboards import (
    main_keyboard, subjects_keyboard, topics_keyboard,
    admin_panel_keyboard, admin_cancel_keyboard, admin_users_keyboard,
    admin_orders_keyboard, order_actions_keyboard, quick_reply_inline_keyboard
)
from services import notify_admin, handle_admin_broadcast, handle_admin_reply, send_message_to_user, \
    send_message_with_notify, notify_user_order_status

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"Пользователь {user.id} запустил бота")

    db.save_user(user.id, user.first_name, user.username)
    db.save_user_activity(user.id, "start", "/start")

    welcome_text = f"""Привет, {user.first_name}! 👋

Мы — команда экспертов с огромным опытом в сфере строительных дисциплин. Наша специализация — выполнение курсовых работ высочайшего качества с полным сопровождением на всех этапах.

Выбери нужный раздел:"""

    await update.message.reply_text(welcome_text, reply_markup=main_keyboard())


async def handle_subjects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📚 Доступные предметы:\n\nВыбери предмет для заказа курсовой работы:"
    await update.message.reply_text(text, reply_markup=subjects_keyboard())


async def handle_subject_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, subject: str):
    user = update.effective_user

    db.save_user_selection(user.id, subject=subject)
    db.save_user_activity(user.id, "subject_selection", f"Выбрал предмет: {subject}")

    text = f"""🎯 Выбран предмет: {subject}

📝 Доступные темы:

Выбери подходящую тему или укажи свою:"""

    await update.message.reply_text(text, reply_markup=topics_keyboard(subject))


async def handle_topic_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, topic: str):
    user = update.effective_user

    selection = db.get_user_selection(user.id)
    if selection and selection.get('subject'):
        subject = selection['subject']

        if topic == "Другая тема (уточнить)":
            db.save_user_selection(user.id, topic=topic)
            db.save_user_activity(user.id, "custom_topic_selected", f"Выбрал свою тему для {subject}")

            text = f"""✏️ Выбрана своя тема

Предмет: {subject}

Напиши свою тему курсовой работы:"""
            await send_message_with_notify(update, context, text, f"Своя тема для {subject}")
        else:
            db.save_user_selection(
                user.id,
                topic=topic,
                price=PRICES['standard']
            )
            db.save_user_activity(user.id, "topic_selection", f"Выбрал тему: {topic} для {subject}")

            text = f"""✅ Тема выбрана!

📚 Предмет: {subject}
📝 Тема: {topic}

💰 Стоимость: {PRICES['standard']} руб.
⏰ Срок выполнения: 7 дней

🛒 Для оформления заказа нажми '🛒 Корзина'"""

            await update.message.reply_text(text, reply_markup=main_keyboard())
            await notify_admin(context.application, user, text, f"Тема: {topic} для {subject}")


async def handle_custom_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    custom_topic = update.message.text

    selection = db.get_user_selection(user.id)
    if selection and selection.get('subject'):
        subject = selection['subject']

        db.save_user_selection(
            user.id,
            custom_topic=custom_topic,
            price=PRICES['custom_topic']
        )
        db.save_user_activity(user.id, "custom_topic_entered", f"Ввел свою тему: {custom_topic} для {subject}")

        text = f"""✅ Ваша тема принята!

📚 Предмет: {subject}
📝 Тема: {custom_topic}

💰 Стоимость: {PRICES['custom_topic']} руб. (индивидуальная тема)
⏰ Срок выполнения: 10 дней

🛒 Для оформления заказа нажми '🛒 Корзина'"""

        await update.message.reply_text(text, reply_markup=main_keyboard())
        await notify_admin(context.application, user, text, f"Своя тема: {custom_topic} для {subject}")
    else:
        await send_message_with_notify(update, context, "Сначала выбери предмет 👆")


async def clear_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    db.delete_user_selection(user.id)
    db.save_user_activity(user.id, "clear_chat", "Очистил чат")

    await send_message_with_notify(update, context, "🧹 Чат полностью очищен!\n\nВсе выборы сброшены.", "Очистка чата")


async def handle_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    selection = db.get_user_selection(user.id)

    if selection and (selection.get('topic') or selection.get('custom_topic')):
        subject = selection.get('subject', 'Не выбран')
        topic = selection.get('custom_topic') or selection.get('topic', 'Не выбрана')
        price = selection.get('price', 0)

        cart_text = f"""🛒 Твой заказ:

📚 Предмет: {subject}
📝 Тема: {topic}
💰 Стоимость: {price} руб.

💳 Для оформления заказа нажмите кнопку ниже👇"""

        keyboard = [
            ['✅ Оформить заказ'],
            ['↩️ Назад в меню']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(cart_text, reply_markup=reply_markup)
        db.save_user_activity(user.id, "cart_view", "Просмотр корзины")

    else:
        await update.message.reply_text(
            "🛒 Корзина пуста. Сначала выбери тему работы!",
            reply_markup=main_keyboard()
        )
        db.save_user_activity(user.id, "empty_cart", "Корзина пуста")


async def create_order_from_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Создает заказ из корзины"""
    user = update.effective_user
    selection = db.get_user_selection(user.id)

    if not selection or not (selection.get('topic') or selection.get('custom_topic')):
        await update.message.reply_text("❌ Нет данных для создания заказа", reply_markup=main_keyboard())
        return

    subject = selection.get('subject', 'Не выбран')
    topic = selection.get('custom_topic') or selection.get('topic', 'Не выбрана')
    price = selection.get('price', 0)

    # Создаем заказ в базе данных
    order_id = db.create_order(user.id, subject, topic, selection.get('custom_topic'), price)

    if order_id:
        # Уведомляем админа о новом заказе
        await notify_admin_new_order(context, user, order_id, subject, topic, price)

        # Очищаем корзину пользователя
        db.delete_user_selection(user.id)

        order_text = f"""✅ Заказ оформлен!

📋 Номер заказа: #{order_id}
📚 Предмет: {subject}
📝 Тема: {topic}
💰 Стоимость: {price} руб.
📞 Статус: {ORDER_STATUSES['working']}

💬 Мы свяжемся с вами в ближайшее время для уточнения деталей."""

        await update.message.reply_text(order_text, reply_markup=main_keyboard())
        db.save_user_activity(user.id, "order_created", f"Создан заказ #{order_id}")

    else:
        await update.message.reply_text("❌ Ошибка при создании заказа", reply_markup=main_keyboard())


async def notify_admin_new_order(context, user, order_id, subject, topic, price):
    """Уведомляет админа о новом заказе"""
    try:
        admin_message = f"""🆕 НОВЫЙ ЗАКАЗ #{order_id}

👤 Пользователь:
🆔 ID: {user.id}
👤 Имя: {user.first_name}
📱 @{user.username if user.username else 'нет'}

📋 Детали заказа:
📚 Предмет: {subject}
📝 Тема: {topic}
💰 Стоимость: {price} руб.
⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}"""

        # Сохраняем message_id для возможного удаления
        sent_message = await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_message,
            reply_markup=order_actions_keyboard(order_id)
        )

        # Можно сохранить message_id в context если нужно будет удалять позже
        # context.bot_data[f'order_{order_id}'] = sent_message.message_id

    except Exception as e:
        logger.error(f"Ошибка уведомления админа о новом заказе: {e}")


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        return

    admin_states[user.id] = 'admin_panel'
    await update.message.reply_text("🛠️ Панель администратора", reply_markup=admin_panel_keyboard())


async def handle_admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        return

    text = update.message.text

    if text == '👥 Пользователи':
        await admin_users(update, context)
    elif text == '📦 Заказы':
        await admin_orders(update, context)
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
    elif text in ['📦 Все заказы', '✅ Готовые заказы', '🔄 Заказы в работе']:
        await handle_orders_filter(update, context, text)


async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает панель управления заказами"""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return

    admin_states[user.id] = 'admin_orders'
    await update.message.reply_text(
        "📦 Управление заказами\n\nВыберите фильтр для просмотра заказов:",
        reply_markup=admin_orders_keyboard()
    )


async def handle_orders_filter(update: Update, context: ContextTypes.DEFAULT_TYPE, filter_type: str):
    """Обрабатывает фильтры заказов"""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return

    if filter_type == '📦 Все заказы':
        orders = db.get_orders("all")
        await show_orders_list(update, orders, "📦 Все заказы")
    elif filter_type == '✅ Готовые заказы':
        orders = db.get_orders(ORDER_STATUSES['ready'])
        await show_orders_list(update, orders, "✅ Готовые заказы")
    elif filter_type == '🔄 Заказы в работе':
        orders = db.get_orders(ORDER_STATUSES['working'])
        await show_individual_orders(update, orders, "🔄 Заказы в работе")
    else:
        return


async def show_orders_list(update: Update, orders: list, title: str):
    """Показывает список заказов одним сообщением"""
    if not orders:
        await update.message.reply_text(
            f"❌ {title.split(' ')[1]} не найдены",
            reply_markup=admin_orders_keyboard()
        )
        return

    orders_text = f"{title} ({len(orders)} шт.):\n\n"

    for i, order in enumerate(orders, 1):
        orders_text += f"🔹 Заказ #{order['order_id']}\n"
        orders_text += f"👤 {order['first_name']}"
        if order['username']:
            orders_text += f" (@{order['username']})"
        orders_text += f"\n📚 {order['subject']}\n"
        orders_text += f"📝 {order['custom_topic'] or order['topic']}\n"
        orders_text += f"💰 {order['price']} руб. | {order['status']}\n"
        orders_text += f"⏰ {order['created_at'][:16]}\n"

        if order['admin_comment']:
            orders_text += f"💬 {order['admin_comment']}\n"

        orders_text += "━━━━━━━━━━━━━━━━━━━━\n\n"

    await update.message.reply_text(orders_text, reply_markup=admin_orders_keyboard())


async def show_individual_orders(update: Update, orders: list, title: str):
    """Показывает каждый заказ отдельным сообщением с кнопками"""
    if not orders:
        await update.message.reply_text(
            f"❌ {title.split(' ')[1]} не найдены",
            reply_markup=admin_orders_keyboard()
        )
        return

    # Сначала отправляем заголовок
    await update.message.reply_text(f"{title} ({len(orders)} шт.):")

    # Затем отправляем каждый заказ отдельным сообщением
    for order in orders:
        order_text = f"""🔹 Заказ #{order['order_id']}

👤 Пользователь:
├ Имя: {order['first_name']}
├ ID: {order['user_id']}
└ @{order['username'] if order['username'] else 'нет'}

📋 Детали заказа:
├ Предмет: {order['subject']}
├ Тема: {order['custom_topic'] or order['topic']}
├ Стоимость: {order['price']} руб.
├ Статус: {order['status']}
└ Создан: {order['created_at'][:16]}

💬 Комментарий: {order['admin_comment'] or 'нет'}"""

        await update.message.reply_text(
            order_text,
            reply_markup=order_actions_keyboard(order['order_id'])
        )


async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    active_users = db.get_active_users(24)

    if not active_users:
        await update.message.reply_text("📭 Нет активных пользователей", reply_markup=admin_panel_keyboard())
        return

    users_text = "👥 Активные пользователи (за последние 24 часа):\n\n"
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
    stats = db.get_user_stats()

    stats_text = f"""📊 Статистика бота

👥 Всего пользователей: {stats['total_users']}
🔥 Активных за 24 часа: {stats['active_today']}
📝 Текущих заказов: {stats['current_orders']}"""

    await update.message.reply_text(stats_text, reply_markup=admin_panel_keyboard())


async def admin_reply_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "❌ Формат: /reply ID ваш_текст\n\nПример: /reply 123456789 Привет! Как дела?")
        return

    try:
        target_user_id = int(context.args[0])
        reply_text = ' '.join(context.args[1:])

        success = await send_message_to_user(context, target_user_id, reply_text, update)

        if success:
            active_users = db.get_active_users(1)
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
        success = await send_message_to_user(context, target_user_id, reply_text, update)

        if success:
            active_users = db.get_active_users(1)
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


async def handle_inline_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    if user.id != ADMIN_ID:
        return

    callback_data = query.data

    if callback_data.startswith('quick_reply_'):
        try:
            user_id = int(callback_data.split('_')[2])
            active_users = db.get_active_users(1)

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

    # Обработка кнопок заказов
    elif callback_data.startswith('order_'):
        await handle_order_actions(update, context, callback_data)


async def handle_order_actions(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
    """Обрабатывает действия с заказами"""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    if user.id != ADMIN_ID:
        return

    try:
        action, order_id = callback_data.split('_')[1], int(callback_data.split('_')[2])

        if action == 'ready':
            success = db.update_order_status(order_id, ORDER_STATUSES['ready'])
            if success:
                # Уведомляем пользователя
                orders = db.get_orders("all")
                target_order = next((o for o in orders if o['order_id'] == order_id), None)
                if target_order:
                    await notify_user_order_status(context, target_order['user_id'], order_id, ORDER_STATUSES['ready'])

                # УДАЛЯЕМ сообщение с заказом
                await query.delete_message()

                # Отправляем подтверждение админу
                await context.bot.send_message(
                    chat_id=user.id,
                    text=f"✅ Заказ #{order_id} отмечен как готовый и удален из списка",
                    reply_markup=admin_orders_keyboard()
                )

        elif action == 'delete':
            success = db.delete_order(order_id)
            if success:
                # УДАЛЯЕМ сообщение с заказом
                await query.delete_message()

                # Отправляем подтверждение админу
                await context.bot.send_message(
                    chat_id=user.id,
                    text=f"🗑️ Заказ #{order_id} удален",
                    reply_markup=admin_orders_keyboard()
                )

    except Exception as e:
        logger.error(f"Ошибка обработки действия с заказом: {e}")
        await context.bot.send_message(
            chat_id=user.id,
            text="❌ Ошибка обработки действия",
            reply_markup=admin_panel_keyboard()
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text

    db.save_user(user.id, user.first_name, user.username)

    # Проверяем специальные состояния
    if user.id == ADMIN_ID and admin_states.get(user.id):
        state = admin_states.get(user.id)

        if state == 'awaiting_broadcast':
            await handle_admin_broadcast(update, context)
        elif isinstance(state, dict) and state.get('mode') == 'awaiting_reply':
            await handle_admin_reply(update, context)
        elif isinstance(state, dict) and state.get('mode') == 'order_comment':
            await handle_order_comment(update, context)
        elif text.startswith('💬 Ответить'):
            try:
                match = re.search(r'ID: (\d+)\)', text)
                if match:
                    user_id = int(match.group(1))
                    active_users = db.get_active_users(1)

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

    # Обработка сообщений пользователя
    if text == '📚 Предметы':
        db.save_user_activity(user.id, "menu_click", "Предметы")
        await handle_subjects(update, context)
    elif text == 'ℹ️ Гарантии':
        db.save_user_activity(user.id, "menu_click", "Гарантии")
        await send_message_with_notify(update, context,
                                       "ℹ️ Наши гарантии:\n\n✅ Качество работ\n✅ Соблюдение сроков\n✅ Конфиденциальность",
                                       "Гарантии")
    elif text == '💰 Цены':
        db.save_user_activity(user.id, "menu_click", "Цены")
        await send_message_with_notify(update, context,
                                       "💰 Наши цены:\n\n📝 Курсовая: от 2000 руб.\n⚡ Срочный заказ: +50%\n📚 Сложный предмет: +30%",
                                       "Цены")
    elif text == '👨‍🎓 О нас':
        db.save_user_activity(user.id, "menu_click", "О нас")
        await send_message_with_notify(update, context,
                                       "👨‍🎓 Профессиональная команда авторов с опытом работы более 5 лет!", "О нас")
    elif text == '🛒 Корзина':
        db.save_user_activity(user.id, "menu_click", "Корзина")
        await handle_cart(update, context)
    elif text == '✅ Оформить заказ':
        db.save_user_activity(user.id, "menu_click", "Оформить заказ")
        await create_order_from_cart(update, context)
    elif text == '📞 Контакты':
        db.save_user_activity(user.id, "menu_click", "Контакты")
        await send_message_with_notify(update, context,
                                       "📞 Наши контакты:\n\n👤 Менеджер: @manager\n📧 Email: info@example.com",
                                       "Контакты")
    elif text == '🧹 Очистить чат':
        db.save_user_activity(user.id, "menu_click", "Очистить чат")
        await clear_chat(update, context)
    elif text in SUBJECTS_TOPICS.keys():
        db.save_user_activity(user.id, "subject_selected", text)
        await handle_subject_selection(update, context, text)
    elif text == '↩️ Назад в меню':
        db.save_user_activity(user.id, "menu_click", "Назад в меню")
        await start(update, context)
    elif text == '↩️ К выбору предмета':
        db.save_user_activity(user.id, "menu_click", "К выбору предмета")
        await handle_subjects(update, context)
    elif text == '🏠 В главное меню':
        db.save_user_activity(user.id, "menu_click", "В главное меню")
        await start(update, context)
    elif any(text in topics for topics in SUBJECTS_TOPICS.values()):
        db.save_user_activity(user.id, "topic_selected", text)
        await handle_topic_selection(update, context, text)
    else:
        selection = db.get_user_selection(user.id)
        if selection and selection.get('topic') == "Другая тема (уточнить)":
            await handle_custom_topic(update, context)
        else:
            db.save_user_activity(user.id, "unknown_message", text)
            await send_message_with_notify(update, context, "Пожалуйста, используй кнопки меню 👆", text)


async def handle_order_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает добавление комментария к заказу"""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return

    state = admin_states.get(user.id)
    if isinstance(state, dict) and state.get('mode') == 'order_comment':
        order_id = state.get('order_id')
        comment = update.message.text

        if comment == '❌ Отмена':
            admin_states[user.id] = 'admin_panel'
            await update.message.reply_text("Добавление комментария отменено", reply_markup=admin_panel_keyboard())
            return

        success = db.update_order_comment(order_id, comment)
        if success:
            admin_states[user.id] = 'admin_panel'
            await update.message.reply_text(
                f"✅ Комментарий добавлен к заказу #{order_id}",
                reply_markup=admin_panel_keyboard()
            )
        else:
            await update.message.reply_text(
                "❌ Ошибка добавления комментария",
                reply_markup=admin_panel_keyboard()
            )