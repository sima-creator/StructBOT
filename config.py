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
        'description': ''
    },
    'standard': {
        'name': '📊 СТАНДАРТ',
        'description': ''
    },
    'individual': {
        'name': '💎 ИНДИВИДУАЛЬНЫЙ',
        'description': ''
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