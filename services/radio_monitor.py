import time
import requests
from config import RADIO_API_URLS
from database import get_db_connection
from services.utils import get_itunes_preview
from services.navidrome import (
    get_target_playlist_id,
    get_playlist_track_ids,
    search_in_navidrome
)
from services.auditor import (
    check_db_status,
    sync_aceptadas_to_libreria,
    sync_playlist_faltantes
)
from services.smart_playlists import sync_all_smart_playlists
from services.radio_stats_service import record_radio_emissions_batch

def radio_monitor_loop():
    """Bucle en segundo plano que monitoriza las emisoras de radio y sincroniza con Navidrome"""
    print("📻 [Monitor Radio] Iniciando monitor de radio en segundo plano...")
    sync_counter = 0
    while True:
        try:
            # 1. Obtener canciones sonando en las radios
            all_songs = []
            for url in RADIO_API_URLS:
                try:
                    res = requests.get(url, timeout=10)
                    if res.status_code == 200:
                        data = res.json()
                        for cat in ['previous', 'now', 'next']:
                            items = data.get('results', {}).get(cat, [])
                            if isinstance(items, dict):
                                items = [items]
                            for item in items:
                                if item.get('song') is True:
                                    all_songs.append({
                                        'title': item.get('name'),
                                        'artist': item.get('artistName'),
                                        'station': item.get('serviceName', 'Desconocida'),
                                        'start_time': item.get('startTime')
                                    })
                except Exception:
                    pass

            # Registrar emisiones para el estudio de rotación de radio
            if all_songs:
                try:
                    record_radio_emissions_batch(all_songs)
                except Exception as ex_em:
                    print(f"Error guardando emisiones de radio: {ex_em}")

            # 2. Playlist actual en Navidrome
            playlist_id = get_target_playlist_id()
            playlist_tracks = get_playlist_track_ids(playlist_id) if playlist_id else set()

            # 3. Procesar canciones encontradas
            for song in all_songs:
                status = check_db_status(song['title'], song['artist'])
                if status:
                    continue # Ya procesada previamente
                
                in_navidrome, nav_id = search_in_navidrome(song['title'], song['artist'])
                preview = get_itunes_preview(song['title'], song['artist'])
                
                if in_navidrome:
                    en_playlist = nav_id in playlist_tracks
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT IGNORE INTO canciones_libreria (title, artist, navidrome_id, en_playlist, preview_url) 
                        VALUES (%s, %s, %s, %s, %s)
                    """, (song['title'], song['artist'], nav_id, en_playlist, preview))
                    conn.commit()
                    cursor.close()
                    conn.close()
                else:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO canciones_descubiertas (title, artist, station, estado, preview_url) 
                        VALUES (%s, %s, %s, 'pendiente', %s)
                    """, (song['title'], song['artist'], song['station'], preview))
                    conn.commit()
                    cursor.close()
                    conn.close()
            
            # 4. Sincronización periódica cada ~30 minutos (15 ciclos * 2 min)
            sync_counter += 1
            if sync_counter >= 15:
                sync_aceptadas_to_libreria()
                sync_playlist_faltantes()
                try:
                    sync_all_smart_playlists()
                except Exception as ex:
                    print(f"Error sincronizando smart playlists en background: {ex}")
                sync_counter = 0

        except Exception as e:
            print(f"Error bucle radio: {e}")
            
        time.sleep(120)
