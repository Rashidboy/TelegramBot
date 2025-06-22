import google.generativeai as genai
import os
import logging
from google.api_core.exceptions import ResourceExhausted # Yangi import

# Gemini API kalitini sozlash
# .env faylidan GEMINI_API_KEY muhit o'zgaruvchisi olinadi
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

async def get_gemini_response(prompt: str) -> str:
    """Gemini modelidan javob oladi."""
    try:
        model = genai.GenerativeModel('models/gemini-1.5-pro-latest') 
        response = await model.generate_content_async(prompt)
        return response.text
    except ResourceExhausted as e:
        logging.error(f"Gemini API bilan ishlashda limit xatosi: {e}")
        # Foydalanuvchiga qulayroq javob
        return (
            "Kechirasiz, AI xizmati hozirda band yoki limitga yetgan bo'lishi mumkin. "
            "Iltimos, bir necha daqiqadan so'ng yoki ertaga qayta urinib ko'ring."
        )
    except Exception as e:
        logging.error(f"Gemini API bilan ishlashda kutilmagan xato: {e}", exc_info=True)
        return "Kechirasiz, AI xizmati bilan bog'liq kutilmagan xatolik yuz berdi. Keyinroq urinib ko'ring."

async def analyze_text_with_gemini(text: str) -> tuple[str, str]:
    """Matnni Gemini yordamida tahlil qiladi (xavfsiz/shubhali)."""
    prompt = (
        f"Quyidagi matnni tahlil qiling va uning xavfli (misol: firibgarlik, yolg'on, spam, reklama, zo'ravonlikka undash) yoki xavfsiz ekanligini aniqlang. "
        f"Javobni faqat 'xavfli: [sababi]' yoki 'xavfsiz: [sababi]' shaklida bering.\n\nMatn: {text}"
    )
    response_text = await get_gemini_response(prompt)
    
    response_text_lower = response_text.lower().strip()
    if "xavfli:" in response_text_lower:
        return "malicious_text", response_text
    elif "xavfsiz:" in response_text_lower:
        return "clean_text", response_text
    else:
        # Agar Gemini javobi kutilgan formatda bo'lmasa, uni to'liq qaytaramiz
        # va holatni 'unknown_text' deb belgilaymiz.
        return "unknown_text", response_text 

async def correct_text_with_gemini(text: str) -> str:
    """Berilgan matndagi xatolarni to'g'irlaydi."""
    prompt = f"Quyidagi matndagi orfografik, grammatik va uslubiy xatolarni to'g'irlab, faqat to'g'irlangan matnni qaytaring:\n\nMatn: {text}"
    return await get_gemini_response(prompt)

async def answer_question_with_gemini(question: str) -> str:
    """Berilgan savolga Gemini yordamida javob beradi."""
    prompt = f"Quyidagi savolga to'liq va aniq javob bering:\n\nSavol: {question}"
    return await get_gemini_response(prompt)