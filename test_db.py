# test_db.py
import mysql.connector
from config.settings import DB_CONFIG

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    print("MySQL ulanish muvaffaqiyatli!")
    conn.close()
except mysql.connector.Error as e:
    print(f"MySQL ulanishda xatolik: {e}")