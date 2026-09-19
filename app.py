import requests
import time
import hashlib
import random
import string
import os
import re
import threading
import mysql.connector
from thefuzz import fuzz
from flask import Flask, render_template, request, redirect, url_for
from dotenv import load_dotenv
import unicodedata

load_dotenv() # Carga las variables desde el archivo .env

# ================= CONFIGURACIÓN =================
RADIO_API_URLS = [
    "https://core-search.radioplayer.cloud/724/qp/v4/events?rpId=404",
    "https://core-search.radioplayer.cloud/724/qp/v4/events?rpId=301",
    "https://core-search.radioplayer.cloud/724/qp/v4/events?rpId=405",
    "https://core-search.radioplayer.cloud/724/qp/v4/events?rpId=402",
    "https://core-search.radioplayer.cloud/724/qp/v4/events?rpId=167"
]

NAVIDROME_URL = os.environ.get("NAVIDROME_URL", "https://tu-navidrome.com")
NAVIDROME_USER = os.environ.get("NAVIDROME_USER", "usuario")
NAVIDROME_PASS = os.environ.get("NAVIDROME_PASS", "")
TARGET_PLAYLIST_NAME = os.environ.get("TARGET_PLAYLIST_NAME", "Canciones que te gustan")

MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASS = os.environ.get("MYSQL_PASS", "")
MYSQL_DB = os.environ.get("MYSQL_DB", "radio_music")

FUZZY_THRESHOLD = 80
# =================================================

app = Flask(__name__)

def get_db_connection():
    return mysql.connector.connect(
        host=MYSQL_HOST, user=MYSQL_USER, password=MYSQL_PASS, database=MYSQL_DB
    )

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Crear tablas base
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS canciones_libreria (
                id INT AUTO_INCREMENT PRIMARY KEY,
                artist VARCHAR(255), title VARCHAR(255),
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_song (artist, title)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS canciones_descubiertas (
                id INT AUTO_INCREMENT PRIMARY KEY,
                artist VARCHAR(255), title VARCHAR(255), station VARCHAR(255),
                estado ENUM('pendiente', 'aceptada', 'rechazada') DEFAULT 'pendiente',
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_song (artist, title)
            )
        """)
        
        # Alterar tablas para añadir columnas nuevas si no existen (Ignoramos errores si ya existen)
        try: cursor.execute("ALTER TABLE canciones_libreria ADD COLUMN navidrome_id VARCHAR(255)")
        except: pass
        try: cursor.execute("ALTER TABLE canciones_libreria ADD COLUMN en_playlist BOOLEAN DEFAULT FALSE")
        except: pass
        try: cursor.execute("ALTER TABLE canciones_libreria ADD COLUMN preview_url TEXT")
        except: pass
        try: cursor.execute("ALTER TABLE canciones_libreria ADD COLUMN ignorar_playlist BOOLEAN DEFAULT FALSE")
        except: pass
        
        try: cursor.execute("ALTER TABLE canciones_descubiertas ADD COLUMN preview_url TEXT")
        except: pass
        
        conn.commit()
        cursor.close()
        conn.close()
        print("Base de datos lista con nueva estructura.")
    except Exception as e:
        print(f"Error inicializando BD: {e}")

# ----- UTILIDADES -----
def clean_text(text):
    if not text: return ""
    text = text.lower()
    # Eliminar acentos y caracteres especiales latinos correctamente (í -> i, ñ -> n)
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    # Eliminar paréntesis y su contenido
    text = re.sub(r'[\(\[].*?[\)\]]', '', text)
    # Eliminar cualquier cosa que no sea alfanumérica
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    return " ".join(text.split())

def is_same_song(song1_title, song1_artist, song2_title, song2_artist):
    c_title1, c_artist1 = clean_text(song1_title), clean_text(song1_artist)
    c_title2, c_artist2 = clean_text(song2_title), clean_text(song2_artist)
    score_title = fuzz.token_set_ratio(c_title1, c_title2)
    score_artist = fuzz.token_set_ratio(c_artist1, c_artist2)
    score_combo = fuzz.token_set_ratio(f"{c_artist1} {c_title1}", f"{c_artist2} {c_title2}")
    return score_combo >= FUZZY_THRESHOLD or (score_title >= FUZZY_THRESHOLD and score_artist >= FUZZY_THRESHOLD)

def get_itunes_preview(title, artist):
    try:
        term = f"{artist} {title}"
        res = requests.get("https://itunes.apple.com/search", params={"term": term, "entity": "song", "limit": 1}, timeout=5)
        data = res.json()
        if data['resultCount'] > 0:
            return data['results'][0].get('previewUrl', '')
    except:
        pass
    return None

# ----- NAVIDROME API (SUBSONIC) -----
def get_navidrome_params(extra_params=None):
    salt = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    token = hashlib.md5((NAVIDROME_PASS + salt).encode('utf-8')).hexdigest()
    params = {'u': NAVIDROME_USER, 't': token, 's': salt, 'v': '1.16.1', 'c': 'radioSync', 'f': 'json'}
    if extra_params:
        params.update(extra_params)
    return params

def search_in_navidrome(title, artist):
    """Devuelve (en_libreria, navidrome_id)"""
    clean_query = f"{clean_text(artist)} {clean_text(title)}"
    params = get_navidrome_params({'query': clean_query})
    try:
        response = requests.get(f"{NAVIDROME_URL}/rest/search3.view", params=params)
        response.raise_for_status()
        songs = response.json().get('subsonic-response', {}).get('searchResult3', {}).get('song', [])
        for s in songs:
            if is_same_song(title, artist, s.get('title', ''), s.get('artist', '')):
                return True, s.get('id')
    except Exception as e:
        print(f"Error Navidrome search: {e}")
    return False, None

def get_target_playlist_id():
    params = get_navidrome_params()
    try:
        response = requests.get(f"{NAVIDROME_URL}/rest/getPlaylists.view", params=params)
        playlists = response.json().get('subsonic-response', {}).get('playlists', {}).get('playlist', [])
        for p in playlists:
            if p.get('name') == TARGET_PLAYLIST_NAME:
                return p.get('id')
    except Exception as e:
        print(f"Error Navidrome getPlaylists: {e}")
    return None

def get_playlist_track_ids(playlist_id):
    params = get_navidrome_params({'id': playlist_id})
    try:
        response = requests.get(f"{NAVIDROME_URL}/rest/getPlaylist.view", params=params)
        tracks = response.json().get('subsonic-response', {}).get('playlist', {}).get('entry', [])
        return {t.get('id') for t in tracks}
    except Exception as e:
        print(f"Error Navidrome getPlaylist: {e}")
    return set()

def add_song_to_playlist(playlist_id, song_id):
    params = get_navidrome_params({'playlistId': playlist_id, 'songIdToAdd': song_id})
    try:
        res = requests.get(f"{NAVIDROME_URL}/rest/updatePlaylist.view", params=params)
        return res.status_code == 200
    except:
        return False

def star_song_in_navidrome(song_id):
    params = get_navidrome_params({'id': song_id})
    try:
        res = requests.get(f"{NAVIDROME_URL}/rest/star.view", params=params)
        return res.status_code == 200
    except:
        return False

# ----- LÓGICA DE MONITOREO -----
def check_db_status(title, artist):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, title, artist, en_playlist FROM canciones_libreria")
        for row in cursor.fetchall():
            if is_same_song(title, artist, row['title'], row['artist']):
                conn.close()
                return 'libreria'
        cursor.execute("SELECT id, title, artist, estado FROM canciones_descubiertas")
        for row in cursor.fetchall():
            if is_same_song(title, artist, row['title'], row['artist']):
                conn.close()
                return row['estado']
        conn.close()
        return None
    except Exception as e:
        return None

def sync_aceptadas_to_libreria():
    playlist_id = get_target_playlist_id()
    playlist_tracks = get_playlist_track_ids(playlist_id) if playlist_id else set()
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, title, artist, preview_url FROM canciones_descubiertas WHERE estado = 'aceptada'")
    for row in cursor.fetchall():
        in_nav, nav_id = search_in_navidrome(row['title'], row['artist'])
        if in_nav:
            print(f"🔄 Canción descargada detectada: {row['title']}. Añadiendo a playlist...")
            
            en_play = nav_id in playlist_tracks
            if playlist_id and not en_play:
                success = add_song_to_playlist(playlist_id, nav_id)
                star_song_in_navidrome(nav_id)
                if success:
                    en_play = True
                    playlist_tracks.add(nav_id)
            
            cursor.execute("""
                INSERT IGNORE INTO canciones_libreria (title, artist, navidrome_id, en_playlist, preview_url) 
                VALUES (%s, %s, %s, %s, %s)
            """, (row['title'], row['artist'], nav_id, en_play, row['preview_url']))
            cursor.execute("DELETE FROM canciones_descubiertas WHERE id = %s", (row['id'],))
    conn.commit()
    conn.close()

def radio_monitor_loop():
    print("Iniciando monitor de radio en segundo plano...")
    sync_counter = 0
    while True:
        try:
            # Obtener canciones de radio
            all_songs = []
            for url in RADIO_API_URLS:
                try:
                    res = requests.get(url)
                    if res.status_code == 200:
                        data = res.json()
                        for cat in ['previous', 'now', 'next']:
                            items = data.get('results', {}).get(cat, [])
                            if isinstance(items, dict): items = [items]
                            for item in items:
                                if item.get('song') == True:
                                    all_songs.append({
                                        'title': item.get('name'), 'artist': item.get('artistName'),
                                        'station': item.get('serviceName', 'Desconocida')
                                    })
                except Exception as e:
                    pass

            # Playlist targeting
            playlist_id = get_target_playlist_id()
            playlist_tracks = get_playlist_track_ids(playlist_id) if playlist_id else set()

            # Procesar
            for song in all_songs:
                status = check_db_status(song['title'], song['artist'])
                if status: continue # Ya procesada (o está en BD)
                
                # Check Navidrome
                in_navidrome, nav_id = search_in_navidrome(song['title'], song['artist'])
                preview = get_itunes_preview(song['title'], song['artist'])
                
                if in_navidrome:
                    en_playlist = nav_id in playlist_tracks
                    conn = get_db_connection()
                    conn.cursor().execute("""
                        INSERT IGNORE INTO canciones_libreria (title, artist, navidrome_id, en_playlist, preview_url) 
                        VALUES (%s, %s, %s, %s, %s)
                    """, (song['title'], song['artist'], nav_id, en_playlist, preview))
                    conn.commit()
                    conn.close()
                else:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO canciones_descubiertas (title, artist, station, estado, preview_url) 
                        VALUES (%s, %s, %s, 'pendiente', %s)
                    """, (song['title'], song['artist'], song['station'], preview))
                    conn.commit()
                    conn.close()
            
            # Sincronización cruzada de Aceptadas -> Libreria
            sync_counter += 1
            if sync_counter >= 15: # 15 ciclos * 2 min = 30 minutos
                sync_aceptadas_to_libreria()
                sync_counter = 0

        except Exception as e:
            print(f"Error bucle: {e}")
            
        time.sleep(120)

# ----- FLASK WEB UI -----
@app.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM canciones_descubiertas WHERE estado = 'aceptada' ORDER BY discovered_at DESC")
    aceptadas = cursor.fetchall()
    
    cursor.execute("SELECT * FROM canciones_descubiertas WHERE estado = 'pendiente' ORDER BY discovered_at DESC")
    pendientes = cursor.fetchall()

    cursor.execute("SELECT * FROM canciones_descubiertas WHERE estado = 'rechazada' ORDER BY discovered_at DESC")
    rechazadas = cursor.fetchall()
    
    cursor.execute("SELECT * FROM canciones_libreria WHERE en_playlist = FALSE AND ignorar_playlist = FALSE ORDER BY added_at DESC")
    sin_playlist = cursor.fetchall()
    
    conn.close()
    return render_template('index.html', aceptadas=aceptadas, pendientes=pendientes, rechazadas=rechazadas, sin_playlist=sin_playlist)

@app.route('/force_sync')
def force_sync():
    # Llama a la misma función que usa el proceso en segundo plano
    sync_aceptadas_to_libreria()
    return redirect(url_for('index'))

@app.route('/add_manual', methods=['POST'])
def add_manual():
    artist = request.form.get('artist')
    title = request.form.get('title')
    if artist and title:
        preview = get_itunes_preview(title, artist)
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO canciones_descubiertas (artist, title, station, estado, preview_url) VALUES (%s, %s, %s, 'aceptada', %s)",
                           (artist, title, 'Manual', preview))
            conn.commit()
            conn.close()
        except: pass
    return redirect(url_for('index'))

@app.route('/change_status/<int:song_id>/<status>')
def change_status(song_id, status):
    if status in ['aceptada', 'rechazada', 'pendiente']:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE canciones_descubiertas SET estado = %s WHERE id = %s", (status, song_id))
            conn.commit()
            conn.close()
        except: pass
    return redirect(url_for('index'))

@app.route('/delete/<int:song_id>')
def delete_song(song_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM canciones_descubiertas WHERE id = %s", (song_id,))
        conn.commit()
        conn.close()
    except: pass
    return redirect(url_for('index'))

@app.route('/ignore_playlist/<int:db_id>')
def ignore_playlist(db_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE canciones_libreria SET ignorar_playlist = TRUE WHERE id = %s", (db_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error omitiendo playlist: {e}")
    return redirect(url_for('index'))

@app.route('/add_to_navidrome_playlist/<int:db_id>')
def add_to_navidrome_playlist_route(db_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT title, artist, navidrome_id FROM canciones_libreria WHERE id = %s", (db_id,))
        row = cursor.fetchone()
        
        if row:
            nav_id = row['navidrome_id']
            # Si la canción es antigua y no tiene ID guardado, lo buscamos sobre la marcha
            if not nav_id:
                in_nav, nav_id = search_in_navidrome(row['title'], row['artist'])
                if nav_id:
                    cursor.execute("UPDATE canciones_libreria SET navidrome_id = %s WHERE id = %s", (nav_id, db_id))
                    conn.commit()
            
            if nav_id:
                playlist_id = get_target_playlist_id()
                success = False
                
                if playlist_id:
                    current_tracks = get_playlist_track_ids(playlist_id)
                    if nav_id in current_tracks:
                        success = True # Ya estaba en la playlist, no la duplicamos
                    else:
                        success = add_song_to_playlist(playlist_id, nav_id)
                
                # Le damos a "Me gusta" (estrella) en Navidrome independientemente de si hay playlist o no
                star_song_in_navidrome(nav_id)
                
                if success:
                    cursor.execute("UPDATE canciones_libreria SET en_playlist = TRUE WHERE id = %s", (db_id,))
                    conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error añadiendo a playlist/favoritos: {e}")
        
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    
    # Iniciar monitor en un hilo
    monitor_thread = threading.Thread(target=radio_monitor_loop, daemon=True)
    monitor_thread.start()
    
    # Iniciar Flask en el hilo principal
    print("Iniciando servidor web en http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
