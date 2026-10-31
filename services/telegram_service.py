import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_THREAD_ID

def send_telegram_notification(title, message, emoji="🎵"):
    """Envía un mensaje formateado al grupo y tema de Telegram configurado"""
    if not TELEGRAM_BOT_TOKEN:
        print("[Telegram] Aviso: TELEGRAM_BOT_TOKEN no configurado en .env.")
        return False, "Falta TELEGRAM_BOT_TOKEN en .env"

    if not TELEGRAM_CHAT_ID:
        print("[Telegram] Aviso: TELEGRAM_CHAT_ID no configurado.")
        return False, "Falta TELEGRAM_CHAT_ID"

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    text = f"<b>{emoji} {title}</b>\n\n{message}"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    if TELEGRAM_THREAD_ID:
        try:
            payload["message_thread_id"] = int(TELEGRAM_THREAD_ID)
        except (ValueError, TypeError):
            pass

    try:
        res = requests.post(url, json=payload, timeout=8)
        data = res.json()
        if data.get("ok"):
            return True, "Mensaje enviado a Telegram"
        else:
            err = data.get("description", "Error desconocido de Telegram")
            print(f"[Telegram] Error API: {err}")
            return False, err
    except Exception as e:
        print(f"[Telegram] Error de conexión: {e}")
        return False, str(e)
