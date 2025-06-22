import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from dotenv import load_dotenv # Muhit o'zgaruvchilarini yuklash uchun
load_dotenv() # .env faylidagi o'zgaruvchilarni yuklash

from telegram.ext import ApplicationBuilder
from telegram import Update
from bot.handlers import get_handlers
from bot.database import connect_db
from bot.logger import setup_logger
import logging

# Logging sozlamalari
setup_logger()

def main():
    # Ma'lumotlar bazasi ulanishi
    conn = connect_db()
    if conn is None:
        logging.error("Ma'lumotlar bazasi ulanmadi, bot ishga tushmaydi!")
        return

    # Application yaratish
    application = ApplicationBuilder().token(os.getenv('BOT_TOKEN')).build()
    application.bot_data["db"] = conn # Ma'lumotlar bazasi ulanishini bot_data ga saqlash

    # Handlers.py dan handler obyektlarini olish
    for handler in get_handlers():
        application.add_handler(handler)
        
    # Botni ishga tushurish
    logging.info("Bot ishga tushirildi va polling rejimida ishlamoqda...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()