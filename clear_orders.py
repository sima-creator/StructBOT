import sqlite3
import os


def clear_orders_completely():
    """Полностью очищает заказы"""
    print("🧹 Начинаем очистку заказов...")

    if not os.path.exists('bot_database.db'):
        print("❌ Файл базы данных не найден!")
        return

    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()

    try:
        # 1. Удаляем все заказы
        cursor.execute('DELETE FROM orders')
        print("✅ Заказы удалены из таблицы")

        # 2. Сбрасываем автоинкремент
        cursor.execute('DELETE FROM sqlite_sequence WHERE name="orders"')
        print("✅ Автоинкремент сброшен")

        # 3. COMMIT - ВАЖНО!
        conn.commit()
        print("✅ Изменения сохранены в базе")

        # 4. Проверяем результат
        cursor.execute('SELECT COUNT(*) FROM orders')
        count = cursor.fetchone()[0]
        print(f"✅ Проверка: заказов в базе - {count}")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        conn.rollback()
    finally:
        conn.close()


def vacuum_database():
    """Оптимизирует базу данных"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('VACUUM')
    conn.commit()
    conn.close()
    print("✅ База данных оптимизирована (VACUUM)")


if __name__ == '__main__':
    clear_orders_completely()
    vacuum_database()
    print("\n🎯 Очистка завершена!")