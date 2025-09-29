import sqlite3
import os


def check_database_state():
    print("🔍 Проверяем состояние базы данных...")

    # Проверяем существует ли файл
    if not os.path.exists('bot_database.db'):
        print("❌ Файл bot_database.db не существует!")
        return

    print(f"✅ Файл базы данных существует: {os.path.getsize('bot_database.db')} байт")

    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()

    try:
        # Проверяем таблицу orders
        cursor.execute('SELECT COUNT(*) FROM orders')
        orders_count = cursor.fetchone()[0]
        print(f"📦 Заказов в таблице: {orders_count}")

        # Показываем все заказы
        cursor.execute('SELECT order_id, user_id, subject, topic FROM orders')
        orders = cursor.fetchall()

        if orders:
            print("\n📋 Список заказов:")
            for order in orders:
                print(f"   #{order[0]} - User:{order[1]} - {order[2]} - {order[3]}")
        else:
            print("✅ Заказов нет - таблица пуста")

        # Проверяем sqlite_sequence
        cursor.execute('SELECT * FROM sqlite_sequence WHERE name="orders"')
        seq = cursor.fetchone()
        if seq:
            print(f"🔢 Автоинкремент orders: {seq[1]}")
        else:
            print("✅ Автоинкремент orders сброшен")

    except Exception as e:
        print(f"❌ Ошибка при проверке: {e}")
    finally:
        conn.close()


if __name__ == '__main__':
    check_database_state()