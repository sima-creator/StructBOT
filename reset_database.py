# reset_database.py
import os


def reset_database():
    print("🔄 Полностью пересоздаем базу данных...")

    if os.path.exists('bot_database.db'):
        os.remove('bot_database.db')
        print("✅ Старая база удалена")

    # Импортируем database чтобы создать новую
    from database import db
    print("✅ Новая база создана с обновленной структурой")


if __name__ == '__main__':
    reset_database()