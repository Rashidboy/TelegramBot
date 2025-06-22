import requests
import time
import os
import logging
from config.settings import VT_API_KEY

def check_url(url: str) -> str:
    """
    Berilgan URLni VirusTotal yordamida tekshiradi.
    Faqat URLlar uchun. APK fayllar uchun alohida funksiya.
    """
    headers = {"x-apikey": VT_API_KEY}
    
    try:
        logging.info(f"VirusTotalga URLni tekshirish uchun yuborilmoqda: {url}")
        # URLni yuborish
        response = requests.post("https://www.virustotal.com/api/v3/urls", data={"url": url}, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()
        analysis_id = data["data"]["id"]

        # Tahlil natijalarini olish uchun biroz kutish
        time.sleep(5) 
        
        # Tahlil natijasini so'rash
        logging.info(f"VirusTotal tahlil natijalari so'ralmoqda: {analysis_id}")
        analysis_response = requests.get(f"https://www.virustotal.com/api/v3/analyses/{analysis_id}", headers=headers, timeout=10)
        analysis_response.raise_for_status()

        analysis_data = analysis_response.json()
        stats = analysis_data["data"]["attributes"]["stats"]

        malicious_votes = stats.get("malicious", 0)
        suspicious_votes = stats.get("suspicious", 0)
        
        if malicious_votes > 0 or suspicious_votes > 0:
            logging.warning(f"URL '{url}' VirusTotal tomonidan xavfli/shubhali deb topildi. Malicious: {malicious_votes}, Suspicious: {suspicious_votes}")
            return "malicious"
        
        logging.info(f"URL '{url}' VirusTotal tomonidan xavfsiz deb topildi.")
        return "clean"

    except requests.exceptions.RequestException as req_err:
        logging.error(f"HTTP so'rovida xatolik yuz berdi (URL): {req_err} (URL: {url})")
        if response and response.status_code == 429:
            logging.warning("VirusTotal API limitiga yetdi (URL).")
            # Bu yerda qayta urinish logikasi bo'lishi mumkin, lekin uni to'xtatish yaxshiroq
            # chunki keyingi urinishlar ham limitga duch kelishi mumkin.
            return "limit_exceeded" # Yangi status
        return "unknown"
    except KeyError as key_err:
        logging.error(f"VirusTotal API javobida kalit topilmadi (URL): {key_err}. Javob: {response.json() if response else 'No response'}")
        return "unknown"
    except Exception as e:
        logging.error(f"VirusTotalni tekshirishda kutilmagan xato (URL): {e} (URL: {url})", exc_info=True)
        return "unknown"

def analyze_apk_file(file_path: str, filename: str) -> str:
    """
    APK faylni VirusTotalga yuklab, tahlil qiladi.
    """
    headers = {"x-apikey": VT_API_KEY}
    
    try:
        logging.info(f"VirusTotalga APK fayl yuklanmoqda: {filename}")
        with open(file_path, "rb") as f:
            files = {"file": (filename, f)}
            # Faylni VirusTotalga yuklash
            response = requests.post("https://www.virustotal.com/api/v3/files", files=files, headers=headers, timeout=60) # Katta fayllar uchun timeout oshirildi
            response.raise_for_status()

        data = response.json()
        analysis_id = data["data"]["id"]

        # Tahlil natijasini olish uchun kutish va so'rov yuborish
        # Fayl tahlili ko'proq vaqt olishi mumkin, shuning uchun poll qilish kerak.
        # Bu yerda oddiy sleep ishlatamiz, lekin real loyihada async poll loop kerak.
        max_attempts = 10
        for i in range(max_attempts):
            time.sleep(10) # Har 10 soniyada tekshirish
            logging.info(f"VirusTotal APK tahlil natijalari so'ralmoqda: {analysis_id} (urinish {i+1}/{max_attempts})")
            analysis_response = requests.get(f"https://www.virustotal.com/api/v3/analyses/{analysis_id}", headers=headers, timeout=10)
            analysis_response.raise_for_status()

            analysis_data = analysis_response.json()
            status = analysis_data["data"]["attributes"]["status"]

            if status == "completed":
                stats = analysis_data["data"]["attributes"]["stats"]
                malicious_votes = stats.get("malicious", 0)
                suspicious_votes = stats.get("suspicious", 0)
                
                if malicious_votes > 0 or suspicious_votes > 0:
                    logging.warning(f"APK fayl '{filename}' VirusTotal tomonidan xavfli/shubhali deb topildi. Malicious: {malicious_votes}, Suspicious: {suspicious_votes}")
                    return "malicious"
                
                logging.info(f"APK fayl '{filename}' VirusTotal tomonidan xavfsiz deb topildi.")
                return "clean"
            elif status == "queued" or status == "not_found": # Fayl hali navbatda yoki topilmadi
                continue # Keyingi urinishga o'tish
            else:
                logging.warning(f"APK tahlilining noma'lum holati: {status}")
                return "unknown"
        
        logging.warning(f"APK fayl tahlili {max_attempts} urinishdan keyin ham yakunlanmadi: {filename}")
        return "analysis_timeout" # Yangi status

    except requests.exceptions.RequestException as req_err:
        logging.error(f"HTTP so'rovida xatolik yuz berdi (APK): {req_err} (File: {filename})")
        if response and response.status_code == 429:
            logging.warning("VirusTotal API limitiga yetdi (APK).")
            return "limit_exceeded"
        return "unknown"
    except KeyError as key_err:
        logging.error(f"VirusTotal API javobida kalit topilmadi (APK): {key_err}. Javob: {response.json() if response else 'No response'}")
        return "unknown"
    except Exception as e:
        logging.error(f"VirusTotalni tekshirishda kutilmagan xato (APK): {e} (File: {filename})", exc_info=True)
        return "unknown"