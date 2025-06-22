import google.generativeai as genai
import os
from dotenv import load_dotenv

# .env faylini yuklash (API kalitingizni olish uchun)
load_dotenv() 

# Gemini API kalitini sozlash
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

print("Mavjud Gemini modellari (generateContent qo'llab-quvvatlanadiganlar):")
for m in genai.list_models():
    if "generateContent" in m.supported_generation_methods:
        print(m.name)