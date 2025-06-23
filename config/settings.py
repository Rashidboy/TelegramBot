import os
from dotenv import load_dotenv

load_dotenv()

# Bot tokeni va boshqa sozlamalar
BOT_TOKEN = os.getenv('BOT_TOKEN')
VT_API_KEY = os.getenv('VT_API_KEY')
GOOGLE_GEMINI_API_KEY = os.getenv('GOOGLE_GEMINI_API_KEY')

# Ma'lumotlar bazasi sozlamalari
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'telegram_bot')
}

# Guruh sozlamalari
ADMIN_WARNING_THRESHOLD = int(os.getenv('ADMIN_WARNING_THRESHOLD', 3))
