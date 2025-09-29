import sqlite3
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_file='bot_database.db'):
        self.db_file = db_file
        self.init_db()

    def get_connection(self):
        """Возвращает соединение с базой данных"""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Инициализация базы данных"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT NOT NULL,
                username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица активностей пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                activity_type TEXT,
                message_text TEXT,
                bot_response TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')

        # Таблица выборов пользователей (обновленная)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_selections (
                user_id INTEGER PRIMARY KEY,
                subject TEXT,
                variant TEXT,
                package TEXT,
                price INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')

        # Таблица заказов (обновленная - добавляем variant и package)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                variant TEXT NOT NULL,
                package TEXT NOT NULL,
                price INTEGER NOT NULL,
                status TEXT DEFAULT '🔄 В работе',
                admin_comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')

        conn.commit()
        conn.close()
        logger.info("✅ База данных инициализирована с обновленной структурой")

    def save_user(self, user_id: int, first_name: str, username: str = None):
        """Сохраняет или обновляет пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT OR REPLACE INTO users (user_id, first_name, username, last_seen)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, first_name, username))
            conn.commit()
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения пользователя {user_id}: {e}")
            conn.rollback()
        finally:
            conn.close()

    def save_user_activity(self, user_id: int, activity_type: str, message_text: str = None, bot_response: str = None):
        """Сохраняет активность пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO user_activities (user_id, activity_type, message_text, bot_response)
                VALUES (?, ?, ?, ?)
            ''', (user_id, activity_type, message_text, bot_response))

            cursor.execute('''
                UPDATE users SET last_seen = CURRENT_TIMESTAMP WHERE user_id = ?
            ''', (user_id,))

            conn.commit()
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения активности пользователя {user_id}: {e}")
            conn.rollback()
        finally:
            conn.close()

    def save_user_selection(self, user_id: int, subject: str = None, variant: str = None,
                            package: str = None, price: int = None):
        """Сохраняет выбор пользователя (обновленная версия)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT user_id FROM user_selections WHERE user_id = ?', (user_id,))
            exists = cursor.fetchone()

            if exists:
                update_fields = []
                params = []

                if subject is not None:
                    update_fields.append("subject = ?")
                    params.append(subject)
                if variant is not None:
                    update_fields.append("variant = ?")
                    params.append(variant)
                if package is not None:
                    update_fields.append("package = ?")
                    params.append(package)
                if price is not None:
                    update_fields.append("price = ?")
                    params.append(price)

                update_fields.append("updated_at = CURRENT_TIMESTAMP")
                params.append(user_id)

                query = f"UPDATE user_selections SET {', '.join(update_fields)} WHERE user_id = ?"
                cursor.execute(query, params)
            else:
                cursor.execute('''
                    INSERT INTO user_selections (user_id, subject, variant, package, price)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, subject, variant, package, price))

            conn.commit()
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения выбора пользователя {user_id}: {e}")
            conn.rollback()
        finally:
            conn.close()

    def get_user_selection(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получает выбор пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT subject, variant, package, price 
                FROM user_selections 
                WHERE user_id = ?
            ''', (user_id,))

            result = cursor.fetchone()
            if result:
                return {
                    'subject': result['subject'],
                    'variant': result['variant'],
                    'package': result['package'],
                    'price': result['price']
                }
            return None
        finally:
            conn.close()

    def delete_user_selection(self, user_id: int):
        """Удаляет выбор пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('DELETE FROM user_selections WHERE user_id = ?', (user_id,))
            conn.commit()
        except Exception as e:
            logger.error(f"❌ Ошибка удаления выбора пользователя {user_id}: {e}")
            conn.rollback()
        finally:
            conn.close()

    def create_order(self, user_id: int, subject: str, variant: str, package: str, price: int) -> int:
        """Создает новый заказ (обновленная версия)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO orders (user_id, subject, variant, package, price)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, subject, variant, package, price))

            order_id = cursor.lastrowid
            conn.commit()
            return order_id
        except Exception as e:
            logger.error(f"❌ Ошибка создания заказа для пользователя {user_id}: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()

    def get_orders(self, status_filter: str = "all") -> List[Dict[str, Any]]:
        """Получает заказы с фильтром по статусу"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            if status_filter == "all":
                cursor.execute('''
                    SELECT o.*, u.first_name, u.username 
                    FROM orders o
                    JOIN users u ON o.user_id = u.user_id
                    ORDER BY o.created_at ASC
                ''')
            else:
                cursor.execute('''
                    SELECT o.*, u.first_name, u.username 
                    FROM orders o
                    JOIN users u ON o.user_id = u.user_id
                    WHERE o.status = ?
                    ORDER BY o.created_at ASC
                ''', (status_filter,))

            results = cursor.fetchall()
            orders = []

            for row in results:
                orders.append({
                    'order_id': row['order_id'],
                    'user_id': row['user_id'],
                    'first_name': row['first_name'],
                    'username': row['username'],
                    'subject': row['subject'],
                    'variant': row['variant'],
                    'package': row['package'],
                    'price': row['price'],
                    'status': row['status'],
                    'admin_comment': row['admin_comment'],
                    'created_at': row['created_at']
                })

            return orders
        except Exception as e:
            logger.error(f"❌ Ошибка получения заказов: {e}")
            return []
        finally:
            conn.close()

    def update_order_status(self, order_id: int, new_status: str) -> bool:
        """Обновляет статус заказа"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                UPDATE orders 
                SET status = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE order_id = ?
            ''', (new_status, order_id))

            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"❌ Ошибка обновления статуса заказа {order_id}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def update_order_comment(self, order_id: int, comment: str) -> bool:
        """Обновляет комментарий к заказу"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                UPDATE orders 
                SET admin_comment = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE order_id = ?
            ''', (comment, order_id))

            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"❌ Ошибка обновления комментария заказа {order_id}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def delete_order(self, order_id: int) -> bool:
        """Удаляет заказ"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('DELETE FROM orders WHERE order_id = ?', (order_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"❌ Ошибка удаления заказа {order_id}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_active_users(self, hours: int = 24) -> Dict[int, Dict[str, Any]]:
        """Получает активных пользователей"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT 
                    u.user_id, 
                    u.first_name, 
                    u.username,
                    ua.activity_type,
                    ua.message_text,
                    ua.bot_response,
                    MAX(ua.created_at) as last_activity_time
                FROM users u
                JOIN user_activities ua ON u.user_id = ua.user_id
                WHERE ua.created_at > datetime('now', ?)
                GROUP BY u.user_id
                ORDER BY last_activity_time DESC
            ''', (f'-{hours} hours',))

            results = cursor.fetchall()
            active_users = {}

            for row in results:
                user_id = row['user_id']
                activity_text = row['message_text'] or row['activity_type'] or 'Нет данных'
                active_users[user_id] = {
                    'first_name': row['first_name'],
                    'username': row['username'],
                    'last_activity': activity_text,
                    'last_activity_time': row['last_activity_time']
                }

            return active_users
        except Exception as e:
            logger.error(f"❌ Ошибка получения активных пользователей: {e}")
            return {}
        finally:
            conn.close()

    def get_user_stats(self) -> Dict[str, Any]:
        """Получает статистику пользователей"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT COUNT(*) as total_users FROM users')
            total_users = cursor.fetchone()['total_users']

            cursor.execute('''
                SELECT COUNT(DISTINCT user_id) as active_today 
                FROM user_activities 
                WHERE created_at > datetime('now', '-24 hours')
            ''')
            active_today = cursor.fetchone()['active_today']

            cursor.execute('SELECT COUNT(*) as current_orders FROM orders')
            current_orders = cursor.fetchone()['current_orders']

            return {
                'total_users': total_users,
                'active_today': active_today,
                'current_orders': current_orders
            }
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return {'total_users': 0, 'active_today': 0, 'current_orders': 0}
        finally:
            conn.close()


# Глобальный экземпляр базы данных
db = Database()