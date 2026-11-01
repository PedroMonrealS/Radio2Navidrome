import os
import requests
from dotenv import load_dotenv

def get_telegram_config():
    """Carga siempre la configuración más reciente del archivo .env"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(base_dir, '.env'), override=True)
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "-1003998145275").strip()
    thread_id = os.environ.get("TELEGRAM_THREAD_ID", "24788").strip()
    return token, chat_id, thread_id

def send_telegram_notification(title, message, emoji="🎵"):
    """Envía un mensaje formateado al grupo y tema de Telegram configurado"""
    token, chat_id, thread_id = get_telegram_config()

    if not token:
        print("[Telegram] Aviso: TELEGRAM_BOT_TOKEN no configurado en .env.")
        return False, "Falta TELEGRAM_BOT_TOKEN en .env"

    if not chat_id:
        print("[Telegram] Aviso: TELEGRAM_CHAT_ID no configurado.")
        return False, "Falta TELEGRAM_CHAT_ID"

    # Obtener nombre del bot para mensajes de ayuda si falla
    bot_username = "bot"
    try:
        me_res = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5).json()
        if me_res.get("ok"):
            bot_username = me_res["result"].get("username", "bot")
    except Exception:
        pass

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    text = f"<b>{emoji} {title}</b>\n\n{message}"

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    if thread_id:
        try:
            payload["message_thread_id"] = int(thread_id)
        except (ValueError, TypeError):
            pass

    try:
        res = requests.post(url, json=payload, timeout=8)
        data = res.json()
        if data.get("ok"):
            return True, f"Mensaje enviado con éxito al tema {thread_id} desde @{bot_username}"
        else:
            err = data.get("description", "Error desconocido de Telegram")
            print(f"[Telegram] Error API: {err}")
            if "chat not found" in err.lower():
                return False, f"Chat no encontrado. Debes añadir al bot @{bot_username} como administrador a tu grupo para que pueda escribir en el tema {thread_id}."
            return False, err
    except Exception as e:
        print(f"[Telegram] Error de conexión: {e}")
        return False, str(e)
