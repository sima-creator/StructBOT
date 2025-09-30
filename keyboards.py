from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton


def main_keyboard():
    keyboard = [
        ['📚 Предметы', 'ℹ️ Гарантии'],
        ['💰 Цены', '👨‍🎓 О нас'],
        ['🛒 Корзина', '📞 Контакты'],
        ['🧹 Очистить корзину']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def subjects_keyboard():
    from config import SUBJECTS
    keyboard = []

    # Разбиваем предметы по 2 в ряд
    for i in range(0, len(SUBJECTS), 2):
        row = SUBJECTS[i:i + 2]
        keyboard.append(row)

    keyboard.append(['↩️ Назад в меню'])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def subject_selected_keyboard():
    """Клавиатура после выбора предмета"""
    return ReplyKeyboardMarkup([
        ['✏️ Ввести вариант'],
        ['↩️ К выбору предмета', '🏠 В главное меню']
    ], resize_keyboard=True)


def service_packages_keyboard():
    """Клавиатура с тарифами"""
    return ReplyKeyboardMarkup([
        ['🏗️ БАЗОВЫЙ', '📊 СТАНДАРТ'],
        ['💎 ИНДИВИДУАЛЬНЫЙ', '📞 Заказать консультацию'],
        ['↩️ Назад']
    ], resize_keyboard=True)


def consultation_keyboard():
    """Клавиатура для консультации"""
    return ReplyKeyboardMarkup([
        ['📞 Связаться с менеджером'],
        ['↩️ Назад к тарифам']
    ], resize_keyboard=True)


def cart_keyboard():
    """Клавиатура для корзины"""
    return ReplyKeyboardMarkup([
        ['✅ Оформить заказ'],
        ['↩️ Назад в меню']
    ], resize_keyboard=True)


def admin_panel_keyboard():
    return ReplyKeyboardMarkup([
        ['👥 Пользователи', '📦 Заказы'],
        ['📢 Общая рассылка', '🚪 Обычный режим']
    ], resize_keyboard=True)


def admin_cancel_keyboard():
    return ReplyKeyboardMarkup([['❌ Отмена']], resize_keyboard=True)


def admin_users_keyboard():
    from database import db
    active_users = db.get_active_users(24)

    keyboard = []
    for user_id, user_info in active_users.items():
        keyboard.append([f"💬 Ответить {user_info.get('first_name', 'Пользователю')} (ID: {user_id})"])

    keyboard.append(['↩️ Назад в админ-панель'])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def admin_orders_keyboard():
    """Клавиатура для управления заказами"""
    return ReplyKeyboardMarkup([
        ['📦 Все заказы', '✅ Готовые заказы'],
        ['🔄 Заказы в работе', '↩️ Назад в админ-панель']
    ], resize_keyboard=True)


def order_actions_keyboard(order_id):
    """Инлайн клавиатура для действий с заказом"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Готов", callback_data=f"order_ready_{order_id}"),
            InlineKeyboardButton("🗑️ Удалить", callback_data=f"order_delete_{order_id}")
        ]
    ])


def quick_reply_inline_keyboard(user_id, user_name):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"💬 Ответить {user_name}",
            callback_data=f"quick_reply_{user_id}"
        )]
    ])