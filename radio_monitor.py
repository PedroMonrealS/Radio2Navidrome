import requests
import time
import hashlib
import random
import string
import os
import re
import mysql.connector
from thefuzz import fuzz

# ================= CONFIGURACIÓN =================
# Puedes añadir más URLs a esta lista separadas por comas
RADIO_API_URLS = [
    "https://core-search.radioplayer.cloud/724/qp/v4/events?rpId=404",
    "https://core-search.radioplayer.cloud/724/qp/v4/events?rpId=301",
    "https://core-search.radioplayer.cloud/724/qp/v4/events?rpId=405",
    "https://core-search.radioplayer.cloud/724/qp/v4/events?rpId=402",
    "https://core-search.radioplayer.cloud/724/qp/v4/events?rpId=167"
]
NAVIDROME_URL = "https://music.pmgha.duckdns.org"
NAVIDROME_USER = "pedro"
NAVIDROME_PASS = "287DryMops"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8107331592:AAEJWhPjKE3tP27m_zCZx5CFKxiSrnvM_94")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "-1003998145275")
TELEGRAM_TOPIC_ID = os.environ.get("TELEGRAM_TOPIC_ID", "21797")

MYSQL_HOST = os.environ.get("MYSQL_HOST", "192.168.100.203")
MYSQL_USER = os.environ.get("MYSQL_USER", "bibliotecaMusical")
MYSQL_PASS = os.environ.get("MYSQL_PASS", "k6)sO*Rhlh/iVWE9")
MYSQL_DB = os.environ.get("MYSQL_DB", "bibliotecaMusical")

FUZZY_THRESHOLD = 80  # Porcentaje mínimo de coincidencia
# =================================================

def get_db_connection():
    # Nos conectamos directamente a la base de datos existente
    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASS,
        database=MYSQL_DB
    )
    return conn

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS canciones_libreria (
                id INT AUTO_INCREMENT PRIMARY KEY,
                artist VARCHAR(255),
                title VARCHAR(255),
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_song (artist, title)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS canciones_deseadas (
                id INT AUTO_INCREMENT PRIMARY KEY,
                artist VARCHAR(255),
                title VARCHAR(255),
                la_quiero BOOLEAN DEFAULT TRUE,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_song (artist, title)
            )
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        print("Base de datos inicializada correctamente.")
    except Exception as e:
        print(f"Error inicializando BD: {e}")

def clean_text(text):
    if not text:
        return ""
    text = text.lower()
    # Eliminar contenido entre paréntesis o corchetes (feat., radio edit, etc.)
    text = re.sub(r'[\(\[].*?[\)\]]', '', text)
    # Reemplazar comas, guiones y caracteres raros por espacios
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    # Eliminar espacios extra
    text = " ".join(text.split())
    return text

def is_same_song(song1_title, song1_artist, song2_title, song2_artist):
    c_title1 = clean_text(song1_title)
    c_artist1 = clean_text(song1_artist)
    c_title2 = clean_text(song2_title)
    c_artist2 = clean_text(song2_artist)
    
    # Comparamos títulos y artistas usando token_set_ratio (ignora orden y palabras duplicadas)
    score_title = fuzz.token_set_ratio(c_title1, c_title2)
    score_artist = fuzz.token_set_ratio(c_artist1, c_artist2)
    
    # También calculamos un score combinado por si el formato es "Artista - Titulo"
    combo1 = f"{c_artist1} {c_title1}"
    combo2 = f"{c_artist2} {c_title2}"
    score_combo = fuzz.token_set_ratio(combo1, combo2)
    
    return score_combo >= FUZZY_THRESHOLD or (score_title >= FUZZY_THRESHOLD and score_artist >= FUZZY_THRESHOLD)

def send_telegram_message(message):
    if TELEGRAM_BOT_TOKEN == "TU_TOKEN_DEL_BOT" or TELEGRAM_CHAT_ID == "TU_CHAT_ID":
        print("⚠️ Faltan configurar el Token o Chat ID de Telegram. No se envió el mensaje.")
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'message_thread_id': TELEGRAM_TOPIC_ID,
        'text': message
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error al enviar mensaje a Telegram: {e}")

def get_radio_songs():
    all_songs = []
    for url in RADIO_API_URLS:
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            for category in ['previous', 'now', 'next']:
                if category in data.get('results', {}):
                    items = data['results'][category]
                    if isinstance(items, dict): items = [items]
                    for item in items:
                        if item.get('song') == True:
                            all_songs.append({
                                'title': item.get('name'),
                                'artist': item.get('artistName'),
                                'station': item.get('serviceName', 'Desconocida')
                            })
        except Exception as e:
            print(f"Error al obtener canciones de la radio {url}: {e}")
    return all_songs

def search_in_navidrome(title, artist):
    salt = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    token = hashlib.md5((NAVIDROME_PASS + salt).encode('utf-8')).hexdigest()
    
    # Buscamos de forma genérica usando texto limpio
    clean_query = f"{clean_text(artist)} {clean_text(title)}"
    
    params = {
        'u': NAVIDROME_USER, 't': token, 's': salt, 'v': '1.16.1', 'c': 'radioSync', 'f': 'json',
        'query': clean_query
    }
    
    try:
        response = requests.get(f"{NAVIDROME_URL}/rest/search3.view", params=params)
        response.raise_for_status()
        data = response.json()
        
        songs = data.get('subsonic-response', {}).get('searchResult3', {}).get('song', [])
        
        # Validar resultados con fuzzy matching
        for s in songs:
            nav_title = s.get('title', '')
            nav_artist = s.get('artist', '')
            if is_same_song(title, artist, nav_title, nav_artist):
                return True
                
        return False
    except Exception as e:
        print(f"Error al buscar en Navidrome: {e}")
        return False

def check_db_status(title, artist):
    """Verifica si la canción ya está en alguna tabla. Retorna: 'libreria', 'deseada', o None"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Primero buscamos en libreria (fuzzy a nivel de DB es complejo, buscamos exacto primero)
        # O recuperamos todas y hacemos fuzzy. Para simplificar, buscamos exacto en BD. 
        # Si no está exacto, confiaremos en la limpieza de texto al insertar.
        c_title = clean_text(title)
        c_artist = clean_text(artist)
        
        # Obtenemos todas y comparamos en Python para ser precisos con el fuzzy
        cursor.execute("SELECT id, title, artist FROM canciones_libreria")
        for row in cursor.fetchall():
            if is_same_song(title, artist, row['title'], row['artist']):
                conn.close()
                return 'libreria'
                
        cursor.execute("SELECT id, title, artist FROM canciones_deseadas")
        for row in cursor.fetchall():
            if is_same_song(title, artist, row['title'], row['artist']):
                conn.close()
                return 'deseada'
                
        conn.close()
        return None
    except Exception as e:
        print(f"Error DB status: {e}")
        return None

def add_to_db(table, title, artist, want_it=True):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if table == "canciones_libreria":
            cursor.execute("INSERT INTO canciones_libreria (title, artist) VALUES (%s, %s)", (title, artist))
        elif table == "canciones_deseadas":
            cursor.execute("INSERT INTO canciones_deseadas (title, artist, la_quiero) VALUES (%s, %s, %s)", (title, artist, want_it))
            
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error guardando en BD ({table}): {e}")

def sync_wanted_songs():
    """Revisa las canciones deseadas (la_quiero=True) y si están en Navidrome las mueve a libreria."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, title, artist FROM canciones_deseadas WHERE la_quiero = TRUE")
        wanted_songs = cursor.fetchall()
        
        for song in wanted_songs:
            if search_in_navidrome(song['title'], song['artist']):
                print(f"🔄 ¡Canción conseguida! Moviendo a librería: {song['artist']} - {song['title']}")
                
                # Mover
                cursor_write = conn.cursor()
                cursor_write.execute("INSERT INTO canciones_libreria (title, artist) VALUES (%s, %s)", (song['title'], song['artist']))
                cursor_write.execute("DELETE FROM canciones_deseadas WHERE id = %s", (song['id'],))
                conn.commit()
                cursor_write.close()
                
        conn.close()
    except Exception as e:
        print(f"Error en sincronización cruzada: {e}")

def main():
    print("Iniciando sistema avanzado de monitorización...")
    init_db()
    
    sync_counter = 0
    
    while True:
        try:
            print("Escaneando radio...")
            songs = get_radio_songs()
            for song in songs:
                status = check_db_status(song['title'], song['artist'])
                
                if status == 'libreria':
                    continue # Ya la tenemos
                elif status == 'deseada':
                    continue # Ya está en pendientes
                    
                print(f"🎵 Nueva canción detectada: {song['artist']} - {song['title']}")
                
                # No está en BD, verificamos Navidrome
                if search_in_navidrome(song['title'], song['artist']):
                    print("✅ Encontrada en Navidrome. Guardando en BD.")
                    add_to_db("canciones_libreria", song['title'], song['artist'])
                else:
                    print("❌ No encontrada. Guardando en deseadas y avisando.")
                    add_to_db("canciones_deseadas", song['title'], song['artist'], want_it=True)
                    msg = f"🎵 Nueva canción descubierta:\nArtista: {song['artist']}\nTítulo: {song['title']}\n📻 Escuchada en: {song['station']}\n\nHa sido añadida a la tabla de deseos."
                    send_telegram_message(msg)
            
            # Cada 10 ciclos (aprox 20 min) revisamos si se han descargado las deseadas
            sync_counter += 1
            if sync_counter >= 10:
                print("Iniciando sincronización de canciones deseadas...")
                sync_wanted_songs()
                sync_counter = 0
                
        except Exception as e:
            print(f"Error en bucle principal: {e}")
            
        print("Esperando 2 minutos...")
        time.sleep(120)

if __name__ == "__main__":
    main()
