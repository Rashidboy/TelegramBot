from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, MessageHandler, ContextTypes, CallbackQueryHandler, filters
from telegram.constants import ParseMode 
from bot.filters import CustomFilters # Hozircha CustomFilters.URL ishlatiladi
from bot.link_checker import check_url, analyze_apk_file # analyze_apk_file ni import qiling
from bot.database import insert_link, get_chat_stats, get_global_stats, update_user_warning_count, get_user_warning_count, get_top_warned_users
from config.settings import ADMIN_WARNING_THRESHOLD
import logging
import os # Fayllarni saqlash va o'chirish uchun

# Bot fayllarni yuklash uchun vaqtinchalik papka
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# CommandHandler obyektlari (oldingidek qoladi)
async def start_command_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"Assalomu alaykum, *{user_name}*! 👋\n"
        "Men havolalarni va APK fayllarini tekshiruvchi botman\\. Havola yoki APK fayl yuboring, "
        "yoki /help buyrug‘ini ishlatib ko‘ring\\!", # Xabar o'zgartirildi
        parse_mode=ParseMode.MARKDOWN_V2
    )
start = CommandHandler("start", start_command_callback)

async def help_command_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*Mavjud buyruqlar:*\n"
        "🌐 /start \\- Botni ishga tushirish\n"
        "❓ /help \\- Yordam\n"
        "📊 /stats \\- Statistika\n\n"
        "Shunchaki havola yoki APK fayl yuboring, men uni tekshiraman va natijani aytaman\\!", # Xabar o'zgartirildi
        parse_mode=ParseMode.MARKDOWN_V2
    )
help_command = CommandHandler("help", help_command_callback)

async def stats_command_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Mening statistikam", callback_data="stats_user")],
        [InlineKeyboardButton("Guruh statistikasi", callback_data="stats_chat")],
        [InlineKeyboardButton("Umumiy statistika", callback_data="stats_global")],
        [InlineKeyboardButton("Eng ko'p ogohlantirilganlar", callback_data="stats_top_warned")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Qanday statistikani ko'rsatay?", reply_markup=reply_markup)

stats_command = CommandHandler("stats", stats_command_callback)


async def stats_callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    conn = context.bot_data.get("db")
    response_text = ""

    if conn is None:
        response_text = "Ma'lumotlar bazasi ulanishi mavjud emas."
    else:
        if query.data == "stats_user":
            user_id = query.from_user.id
            user_warning_count = get_user_warning_count(conn, user_id)
            response_text = f"Sizning ogohlantirishlaringiz soni: *{user_warning_count}* ta\\."
        elif query.data == "stats_chat":
            chat_id = query.message.chat_id
            stats = get_chat_stats(conn, chat_id)
            if not stats:
                response_text = "Bu chatda hozircha statistika yo‘q\\."
            else:
                response_text = "*Bu chat statistikasi:*\n"
                for status, count in stats:
                    response_text += f"*{status.replace('_', ' ').title()}:* {count} ta\n"
        elif query.data == "stats_global":
            stats = get_global_stats(conn)
            if not stats:
                response_text = "Umumiy statistika hozircha mavjud emas\\."
            else:
                response_text = "*Umumiy bot statistikasi:*\n"
                for status, count in stats:
                    response_text += f"*{status.replace('_', ' ').title()}:* {count} ta\n"
        elif query.data == "stats_top_warned":
            top_users = get_top_warned_users(conn)
            if not top_users:
                response_text = "Eng ko'p ogohlantirilgan foydalanuvchilar ro'yxati bo'sh\\."
            else:
                response_text = "*Eng ko'p ogohlantirilgan foydalanuvchilar:*\n"
                for i, (username, count) in enumerate(top_users):
                    response_text += f"{i+1}\\. {username or 'Noma\'lum foydalanuvchi'} \\- *{count}* ta ogohlantirish\n"
        
    await query.edit_message_text(response_text, parse_mode=ParseMode.MARKDOWN_V2)

# --- Xabar tekshiruvchi funksiya (URL va Fayl uchun birlashtiriladi) ---
async def _handle_message_for_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name or ""
    message_id = message.message_id
    conn = context.bot_data.get("db")
    
    if conn is None:
        await message.reply_text("Ma'lumotlar bazasi ulanishi mavjud emas, tekshirib bo'lmadi.")
        logging.error("Ma'lumotlar bazasi ulanishi mavjud emas.")
        return

    status = "unknown"
    processing_message = None
    file_path = None # Fayl yo'li, agar fayl bo'lsa

    try:
        if message.text and CustomFilters.URL.check_update(update): # Agar matn va URL bo'lsa
            url = message.text
            processing_message = await message.reply_text("🔗 Havola tekshirilmoqda, iltimos kuting...")
            status = check_url(url)
            insert_link(conn, url, user_id, username, status, chat_id, message_id)

            if status == "malicious":
                response_text = "⚠️ Bu havola *xavfli* deb topildi\\! Iltimos, ehtiyot bo‘ling\\!"
                await message.reply_text(response_text, parse_mode=ParseMode.MARKDOWN_V2)
                # Xavfli xabar mantiqi... (oldingidek)
                await handle_malicious_content_action(update, context, url, user_id, username, first_name, last_name, conn)

            elif status == "limit_exceeded": # Yangi status
                response_text = "⚠️ VirusTotal API limiti oshib ketdi\\. Iltimos, birozdan so'ng qayta urinib ko'ring\\."
                await message.reply_text(response_text, parse_mode=ParseMode.MARKDOWN_V2)

            elif status == "clean":
                response_text = "✅ Bu havola *xavfsiz* ko‘rinadi\\!"
                await message.reply_text(response_text, parse_mode=ParseMode.MARKDOWN_V2)
            else:
                response_text = "❓ Havolani tekshirishda xatolik yuz berdi yoki noma'lum holat\\."
                await message.reply_text(response_text, parse_mode=ParseMode.MARKDOWN_V2)

        elif message.document: # Agar fayl bo'lsa
            doc = message.document
            file_id = doc.file_id
            file_name = doc.file_name
            file_size = doc.file_size

            # Faqat APK fayllarni qabul qilish
            if not file_name.lower().endswith('.apk'):
                await message.reply_text("Kechirasiz, men faqat *\\.apk* fayllarni tekshira olaman\\.", parse_mode=ParseMode.MARKDOWN_V2)
                return

            # Fayl hajmini cheklash (masalan, 50MB)
            if file_size > 50 * 1024 * 1024: 
                await message.reply_text("Kechirasiz, fayl hajmi juda katta (maks 50MB)\\. Kichikroq fayl yuboring\\.", parse_mode=ParseMode.MARKDOWN_V2)
                return
            
            processing_message = await message.reply_text(f"📥 '{file_name}' fayli yuklab olinmoqda va tekshirilmoqda\\. Iltimos kuting, bu biroz vaqt olishi mumkin\\.\\.", parse_mode=ParseMode.MARKDOWN_V2)

            # Faylni yuklab olish
            file_obj = await context.bot.get_file(file_id)
            file_path = os.path.join(DOWNLOAD_DIR, file_name)
            await file_obj.download_to_drive(file_path)
            logging.info(f"Fayl yuklab olindi: {file_name} -> {file_path}")

            status = analyze_apk_file(file_path, file_name)
            # insert_link funksiyasini yangilab, fayllarni ham saqlashi kerak,
            # yoki yangi jadval yaratish kerak bo'lishi mumkin. Hozircha uni URL kabi saqlaymiz,
            # url ustuniga fayl nomini yozib.
            insert_link(conn, file_name, user_id, username, status, chat_id, message_id) # 'url' o'rniga file_name
            
            if status == "malicious":
                response_text = "🚨 Yuklangan *APK fayl xavfli* deb topildi\\! Iltimos, uni o'rnatmang\\!"
                await message.reply_text(response_text, parse_mode=ParseMode.MARKDOWN_V2)
                # Xavfli fayl mantiqi... (oldingidek)
                await handle_malicious_content_action(update, context, file_name, user_id, username, first_name, last_name, conn)

            elif status == "clean":
                response_text = "✅ Yuklangan *APK fayl xavfsiz* ko‘rinadi\\!"
                await message.reply_text(response_text, parse_mode=ParseMode.MARKDOWN_V2)
            elif status == "limit_exceeded":
                response_text = "⚠️ VirusTotal API limiti oshib ketdi\\. Iltimos, birozdan so'ng qayta urinib ko'ring\\."
                await message.reply_text(response_text, parse_mode=ParseMode.MARKDOWN_V2)
            elif status == "analysis_timeout":
                response_text = "⏳ APK fayl tahlili uzoq davom etdi yoki yakunlanmadi\\. Keyinroq urinib ko'ring\\."
                await message.reply_text(response_text, parse_mode=ParseMode.MARKDOWN_V2)
            else:
                response_text = "❓ APK faylni tekshirishda xatolik yuz berdi yoki noma'lum holat\\."
                await message.reply_text(response_text, parse_mode=ParseMode.MARKDOWN_V2)
        else:
            # Agar URL yoki APK fayl bo'lmasa, umumiy javob
            await message.reply_text("Kechirasiz, men faqat havolalarni yoki APK fayllarni tekshira olaman\\. /help buyrug'ini ishlatib ko'ring\\.", parse_mode=ParseMode.MARKDOWN_V2)
            return # Fayl yoki URL bo'lmasa, pastga tushmaslik kerak.

    except Exception as e:
        logging.error(f"Xabarni skanlashda kutilmagan xato: {e}", exc_info=True)
        await message.reply_text("Kutilmagan xatolik yuz berdi\\. Keyinroq urinib ko'ring\\.", parse_mode=ParseMode.MARKDOWN_V2)
    finally:
        # Tekshiruv xabarini o'chirish
        if processing_message:
            try:
                await processing_message.delete()
            except Exception as e:
                logging.warning(f"Processing message ni o'chirishda xato: {e}")
        # Yuklab olingan faylni o'chirish
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logging.info(f"Yuklab olingan fayl o'chirildi: {file_path}")
            except Exception as e:
                logging.error(f"Yuklab olingan faylni o'chirishda xato: {e}")

# Xavfli kontent uchun umumiy harakat (URL va Fayl uchun)
async def handle_malicious_content_action(update: Update, context: ContextTypes.DEFAULT_TYPE, content_info: str, user_id: int, username: str, first_name: str, last_name: str, conn):
    """Xavfli kontent aniqlanganda bajariladigan umumiy amallar."""
    try:
        # Agar guruhda bo'lsa va bot admin bo'lsa, xabarni o'chirish
        if update.effective_chat.type in ["group", "supergroup"]:
            try:
                await update.effective_message.delete()
                logging.info(f"Xavfli kontent o'chirildi: {content_info} (User: {username}, Chat: {update.effective_chat.id})")
                
                update_user_warning_count(conn, user_id, username, first_name, last_name)
                current_warnings = get_user_warning_count(conn, user_id)
                
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"❌ *{username}* tomonidan yuborilgan xavfli kontent o'chirildi\\.\n"
                         f"Bu sizning *{current_warnings}*\\-chi ogohlantirishingiz\\.",
                    parse_mode=ParseMode.MARKDOWN_V2
                )
                
                if current_warnings >= ADMIN_WARNING_THRESHOLD:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"🚨 *DIQQAT*: *{username}* ({current_warnings} ta ogohlantirish) xavfli xatti-harakat uchun guruhdan chiqarilishi mumkin\\."
                             "\nIltimos, guruh qoidalariga rioya qiling\\.",
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
                    # Bu yerda foydalanuvchini ban qilish yoki boshqa admin xabar berish logikasi bo'ladi
                    # Masalan: await context.bot.ban_chat_member(chat_id, user_id)
            except Exception as e:
                logging.error(f"Guruhda xavfli xabarni o'chirishda xato: {e}", exc_info=True)
                await context.bot.send_message(chat_id=update.effective_chat.id, text="Xavfli kontentni o'chirishda xatolik yuz berdi\\. Iltimos, botga 'xabarlarni o'chirish' ruxsatini bering\\.")
    except Exception as e:
        logging.error(f"Xavfli kontent harakatini bajarishda kutilmagan xato: {e}", exc_info=True)


# MessageHandlerlar
# Endi bitta MessageHandler hamma tekshiriladigan xabarlarni ushlaydi
scan_message_handler = MessageHandler(CustomFilters.URL | filters.Document.MimeType("application/vnd.android.package-archive"), _handle_message_for_scan)

# Handlerlarni ro'yxatdan o'tkazish uchun yordamchi funksiya
def get_handlers():
    return [
        start,
        help_command,
        stats_command,
        scan_message_handler, # Yangi MessageHandler
        CallbackQueryHandler(stats_callback_query_handler, pattern="^stats_")
    ]