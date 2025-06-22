import mysql.connector
from config.settings import DB_CONFIG
import logging

def connect_db():
    """Ma'lumotlar bazasiga ulanishni o'rnatadi va jadvallarni yaratadi."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        logging.info("MySQL ma'lumotlar bazasiga muvaffaqiyatli ulanish.")
        create_tables(conn) # Jadvallarni yaratish funksiyasini chaqirish
        return conn
    except mysql.connector.Error as e:
        logging.error(f"MySQL ulanishda xatolik: {e}")
        return None

def create_tables(conn):
    """Kerakli ma'lumotlar bazasi jadvallarini yaratadi."""
    cursor = conn.cursor()
    try:
        # links jadvali: Havolalar ma'lumotlari
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS links (
                id INT AUTO_INCREMENT PRIMARY KEY,
                url TEXT NOT NULL,
                user_id BIGINT,
                username VARCHAR(255),
                status VARCHAR(50),
                chat_id BIGINT,
                message_id BIGINT,
                checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        # users jadvali: Foydalanuvchilar va ularning ogohlantirishlari
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY,
                username VARCHAR(255),
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                warning_count INT DEFAULT 0,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        conn.commit()
        logging.info("Ma'lumotlar bazasi jadvallari yaratildi/mavjud.")
    except mysql.connector.Error as e:
        logging.error(f"Jadvallarni yaratishda xatolik: {e}")
    finally:
        cursor.close()

def insert_link(conn, url, user_id, username, status, chat_id, message_id):
    """Tekshirilgan havolani ma'lumotlar bazasiga kiritadi."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO links (url, user_id, username, status, chat_id, message_id) VALUES (%s, %s, %s, %s, %s, %s)",
            (url, user_id, username, status, chat_id, message_id)
        )
        conn.commit()
        logging.info(f"Havola saqlandi: {url}, Status: {status}")
    except mysql.connector.Error as e:
        logging.error(f"Havolani saqlashda xatolik: {e}")
    finally:
        cursor.close()

def get_chat_stats(conn, chat_id):
    """Berilgan chat bo'yicha havolalar statistikasini qaytaradi."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT status, COUNT(*) as count FROM links WHERE chat_id = %s GROUP BY status",
            (chat_id,)
        )
        stats = cursor.fetchall()
        return stats
    except mysql.connector.Error as e:
        logging.error(f"Chat statistikasi olishda xatolik: {e}")
        return []
    finally:
        cursor.close()

def get_global_stats(conn):
    """Umumiy havolalar statistikasini qaytaradi."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT status, COUNT(*) as count FROM links GROUP BY status"
        )
        stats = cursor.fetchall()
        return stats
    except mysql.connector.Error as e:
        logging.error(f"Global statistika olishda xatolik: {e}")
        return []
    finally:
        cursor.close()

def update_user_warning_count(conn, user_id, username, first_name, last_name, increment=1):
    """Foydalanuvchining ogohlantirishlar sonini yangilaydi yoki foydalanuvchini kiritadi."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (id, username, first_name, last_name, warning_count) VALUES (%s, %s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE warning_count = warning_count + %s, username = %s, first_name = %s, last_name = %s",
            (user_id, username, first_name, last_name, increment, increment, username, first_name, last_name)
        )
        conn.commit()
        logging.info(f"Foydalanuvchi {username} ({user_id}) ogohlantirish soni yangilandi.")
    except mysql.connector.Error as e:
        logging.error(f"Foydalanuvchi ogohlantirish sonini yangilashda xatolik: {e}")
    finally:
        cursor.close()

def get_user_warning_count(conn, user_id):
    """Foydalanuvchining ogohlantirishlar sonini qaytaradi."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT warning_count FROM users WHERE id = %s",
            (user_id,)
        )
        result = cursor.fetchone()
        return result[0] if result else 0
    except mysql.connector.Error as e:
        logging.error(f"Foydalanuvchi ogohlantirish sonini olishda xatolik: {e}")
        return 0
    finally:
        cursor.close()

def get_top_warned_users(conn, limit=5):
    """Eng ko'p ogohlantirilgan foydalanuvchilar ro'yxatini qaytaradi."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT username, warning_count FROM users ORDER BY warning_count DESC LIMIT %s",
            (limit,)
        )
        results = cursor.fetchall()
        return results
    except mysql.connector.Error as e:
        logging.error(f"Eng ko'p ogohlantirilgan foydalanuvchilarni olishda xatolik: {e}")
        return []
    finally:
        cursor.close()