import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))

# Предметы
SUBJECTS = [
    '🏠 Архитектура',
    '🏗️ ТСП',
    '🌡️ ТГВ',
    '🚰 ВиВ'
]

# Цены для каждого предмета по тарифам
SUBJECT_PRICES = {
    '🏠 Архитектура': {
        'basic': 3000,
        'standard': 5000,
        'individual': 7000
    },
    '🏗️ ТСП': {
        'basic': 2500,
        'standard': 4500,
        'individual': 6500
    },
    '🌡️ ТГВ': {
        'basic': 2800,
        'standard': 4800,
        'individual': 6800
    },
    '🚰 ВиВ': {
        'basic': 2700,
        'standard': 4700,
        'individual': 6700
    }
}

# Описания тарифов
SERVICE_PACKAGES = {
    'basic': {
        'name': '🏗️ БАЗОВЫЙ',
        'description': '• Теоретическая часть\n• Основные расчеты\n• Оформление по ГОСТ'
    },
    'standard': {
        'name': '📊 СТАНДАРТ',
        'description': '• Всё из Базового +\n• Чертежи в AutoCAD\n• 3D-визуализация'
    },
    'individual': {
        'name': '💎 ИНДИВИДУАЛЬНЫЙ',
        'description': '• Полное сопровождение\n• Персональный куратор\n• Неограниченные правки\n• Приоритетное выполнение'
    }
}

# Статусы заказов
ORDER_STATUSES = {
    'working': '🔄 В работе',
    'ready': '✅ Готов',
    'delivered': '📦 Передан клиенту',
    'paid': '💰 Оплачен'
}

# Состояния админа и пользователей
admin_states = {}
user_states = {}