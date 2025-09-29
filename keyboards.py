from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton


def main_keyboard():
    keyboard = [
        ['📚 Предметы', 'ℹ️ Гарантии'],
        ['💰 Цены', '👨‍🎓 О нас'],
        ['🛒 Корзина', '📞 Контакты'],
        ['🧹 Очистить чат']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def subjects_keyboard():
    keyboard = [
        ['🏠 Архитектура', '🏗️ ТСП'],
        ['🌡️ ТГВ', '🚰 ВиВ'],
        ['↩️ Назад в меню']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def topics_keyboard(subject):
    from config import SUBJECTS_TOPICS
    topics = SUBJECTS_TOPICS.get(subject, [])
    keyboard = []

    for i in range(0, len(topics), 2):
        row = topics[i:i + 2]
        keyboard.append(row)

    keyboard.append(['↩️ К выбору предмета', '🏠 В главное меню'])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def admin_panel_keyboard():
    return ReplyKeyboardMarkup([
        ['👥 Пользователи', '📊 Статистика'],
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


def quick_reply_inline_keyboard(user_id, user_name):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"💬 Ответить {user_name}",
            callback_data=f"quick_reply_{user_id}"
        )]
    ])