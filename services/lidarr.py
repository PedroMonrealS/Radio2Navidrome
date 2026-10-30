import time
import threading
import requests
from thefuzz import fuzz
from config import LIDARR_URL, LIDARR_API, QBIT_URL, QBIT_USER, QBIT_PASS
from services.utils import clean_text

def request_lidarr_song(artist, title):
    """Envía la petición de búsqueda y descarga de una canción a Lidarr"""
    if not LIDARR_URL:
        return False, "Error: La URL de Lidarr no está configurada en .env o el programa no se ha reiniciado."
    headers = {"X-Api-Key": LIDARR_API}
    proxies = {"http": None, "https": None}
    try:
        res = requests.get(
            f"{LIDARR_URL}/api/v1/artist/lookup",
            params={"term": artist},
            headers=headers,
            proxies=proxies,
            timeout=30
        )
        if res.status_code != 200 or not res.json():
            return False, "Artista no encontrado en Lidarr/MusicBrainz."
        
        best_artist = res.json()[0]
        artist_id = best_artist.get("id")
        
        if not artist_id:
            roots = requests.get(f"{LIDARR_URL}/api/v1/rootfolder", headers=headers, proxies=proxies, timeout=30).json()
            q_profiles = requests.get(f"{LIDARR_URL}/api/v1/qualityprofile", headers=headers, proxies=proxies, timeout=30).json()
            m_profiles = requests.get(f"{LIDARR_URL}/api/v1/metadataprofile", headers=headers, proxies=proxies, timeout=30).json()
            
            if not roots or not q_profiles or not m_profiles:
                return False, "Faltan perfiles (Root/Quality/Metadata) en Lidarr."
                
            payload = best_artist
            payload["qualityProfileId"] = q_profiles[0]["id"]
            payload["metadataProfileId"] = m_profiles[0]["id"]
            payload["rootFolderPath"] = roots[0]["path"]
            payload["monitored"] = True
            payload["addOptions"] = {"monitor": "none"}
            
            add_res = requests.post(f"{LIDARR_URL}/api/v1/artist", json=payload, headers=headers, proxies=proxies, timeout=30).json()
            artist_id = add_res.get("id")
            if not artist_id:
                return False, "Error al añadir el artista a Lidarr."
            
            # El artista es nuevo, Lidarr necesita unos segundos para descargar su discografía de MusicBrainz
            time.sleep(5) 
            
        # Intentar obtener los álbumes (con reintentos si el artista es nuevo)
        albums = []
        for _ in range(3):
            albums = requests.get(f"{LIDARR_URL}/api/v1/album", params={"artistId": artist_id}, headers=headers, proxies=proxies, timeout=30).json()
            if albums:
                break
            time.sleep(3)
            
        if not albums:
            return False, "El artista se añadió, pero aún no tiene álbumes listados en Lidarr. Inténtalo en un rato."
            
        # 1. Buscar entre las pistas del artista para encontrar a qué álbum pertenece la canción
        tracks = requests.get(f"{LIDARR_URL}/api/v1/track", params={"artistId": artist_id}, headers=headers, proxies=proxies, timeout=30).json()
        
        target_album_id = None
        best_track_score = 0
        for t in tracks:
            score = fuzz.partial_ratio(title.lower(), t.get("title", "").lower())
            if score > best_track_score:
                best_track_score = score
                target_album_id = t.get("albumId")
                
        best_album = None
        # Si hemos encontrado la canción con buena precisión, cogemos su álbum
        if target_album_id and best_track_score > 75:
            best_album = next((a for a in albums if a["id"] == target_album_id), None)
            
        # 2. Si no encontró la pista (o falló), intentamos buscar si el álbum se llama igual que la canción (Single)
        if not best_album:
            best_score = 0
            for alb in albums:
                score = fuzz.partial_ratio(title.lower(), alb.get("title", "").lower())
                if score > best_score:
                    best_score = score
                    best_album = alb
            if best_score <= 70:
                best_album = None
                
        # 3. Si por fin tenemos un álbum claro, lo marcamos para vigilar y lo mandamos a buscar
        if best_album:
            alb_id = best_album["id"]
            best_album["monitored"] = True
            requests.put(f"{LIDARR_URL}/api/v1/album/{alb_id}", json=best_album, headers=headers, proxies=proxies, timeout=30)
            
            cmd = {"name": "AlbumSearch", "albumIds": [alb_id]}
            requests.post(f"{LIDARR_URL}/api/v1/command", json=cmd, headers=headers, proxies=proxies, timeout=30)
            return True, f"Búsqueda lanzada para el disco: {best_album.get('title')}"
        else:
            return False, "Artista detectado, pero MusicBrainz/Lidarr no tiene registrado ningún disco/single con esta canción."
    except Exception as e:
        print(f"Error Lidarr: {e}")
        return False, f"Excepción contactando a Lidarr: {e}"

def get_live_download_status(artist):
    """Consulta en tiempo real la cola de Lidarr y de qBittorrent para un artista"""
    try:
        # 1. Lidarr Queue
        headers = {"X-Api-Key": LIDARR_API}
        queue = requests.get(f"{LIDARR_URL}/api/v1/queue", headers=headers, timeout=5).json()
        for item in queue.get('records', []):
            if clean_text(artist) in clean_text(item.get('artist', {}).get('name', '')):
                stat = item.get('status', '')
                if stat == 'Downloading':
                    stat = 'Descargando'
                return {"status_text": f"⏳ Lidarr: {stat}", "color": "#17a2b8"}
                
        # 2. qBittorrent
        session = requests.Session()
        session.post(f"{QBIT_URL}/api/v2/auth/login", data={"username": QBIT_USER, "password": QBIT_PASS}, timeout=5)
        torrents = session.get(f"{QBIT_URL}/api/v2/torrents/info", timeout=5).json()
        
        for t in torrents:
            if clean_text(artist) in clean_text(t.get('name', '')):
                prog = round(t.get('progress', 0) * 100, 1)
                state = t.get('state', '')
                
                color = "#007bff"
                text_state = state
                if "downloading" in state.lower():
                    text_state = "Descargando"
                    color = "#007bff"
                elif "stalled" in state.lower():
                    text_state = "Sin semillas"
                    color = "#ffc107"
                elif "paused" in state.lower():
                    text_state = "Pausado"
                    color = "#6c757d"
                elif "uploading" in state.lower() or prog == 100:
                    text_state = "Completado"
                    color = "#28a745"
                
                return {"status_text": f"📥 Torrent: {prog}% ({text_state})", "color": color}
                
        return {"status_text": "🔍 Buscando origen / Sin semillas", "color": "#6c757d"}
    except Exception as e:
        return {"status_text": "✗ Error conectando a Qbit", "color": "#dc3545"}

# ================= PROCESAMIENTO EN LOTE (BATCH) =================
batch_status = {
    "running": False,
    "total": 0,
    "current": 0,
    "current_song": "",
    "success_count": 0,
    "error_count": 0,
    "message": ""
}

def get_lidarr_batch_status():
    return batch_status

def _batch_worker():
    from database import get_db_connection
    global batch_status
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # 1. Priorizar canciones que aún no se han enviado
        cursor.execute("SELECT id, title, artist FROM canciones_descubiertas WHERE estado = 'aceptada' AND (lidarr_status != 'enviado' OR lidarr_status IS NULL)")
        pending = cursor.fetchall()
        
        # 2. Si todas ya estaban marcadas como enviadas, pero el usuario pulsa pedir todos, las procesa todas
        if not pending:
            cursor.execute("SELECT id, title, artist FROM canciones_descubiertas WHERE estado = 'aceptada'")
            pending = cursor.fetchall()
            
        cursor.close()
        conn.close()
        
        batch_status["total"] = len(pending)
        batch_status["current"] = 0
        batch_status["success_count"] = 0
        batch_status["error_count"] = 0
        
        if not pending:
            batch_status["running"] = False
            batch_status["message"] = "No hay canciones pendientes para pedir a Lidarr."
            return

        for song in pending:
            batch_status["current"] += 1
            batch_status["current_song"] = f"{song['artist']} - {song['title']}"
            
            success, msg = request_lidarr_song(song['artist'], song['title'])
            
            if success:
                batch_status["success_count"] += 1
                try:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("UPDATE canciones_descubiertas SET lidarr_status = 'enviado' WHERE id = %s", (song['id'],))
                    conn.commit()
                    cur.close()
                    conn.close()
                except Exception as e:
                    print(f"Error actualizando lidarr_status de canción {song['id']}: {e}")
            else:
                batch_status["error_count"] += 1
                
            time.sleep(1) # Pausa preventiva para evitar saturar Lidarr y MusicBrainz
            
        batch_status["message"] = f"Finalizado: {batch_status['success_count']} enviadas con éxito, {batch_status['error_count']} fallidas/omitidas."
    except Exception as e:
        batch_status["message"] = f"Error en lote: {e}"
    finally:
        batch_status["running"] = False

def start_batch_request_lidarr():
    global batch_status
    if batch_status["running"]:
        return False, "Ya hay un proceso en ejecución."
    
    batch_status["running"] = True
    batch_status["total"] = 0
    batch_status["current"] = 0
    batch_status["current_song"] = "Iniciando..."
    batch_status["success_count"] = 0
    batch_status["error_count"] = 0
    batch_status["message"] = "En proceso..."
    
    t = threading.Thread(target=_batch_worker, daemon=True)
    t.start()
    return True, "Proceso iniciado correctamente en segundo plano."

