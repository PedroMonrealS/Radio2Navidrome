import time
from concurrent.futures import ThreadPoolExecutor
from database import get_db_connection
from services.utils import is_same_song, get_itunes_preview
from services.navidrome import (
    get_target_playlist_id,
    get_playlist_track_ids,
    get_navidrome_song,
    find_song_in_navidrome,
    search_in_navidrome,
    add_song_to_playlist,
    star_song_in_navidrome
)

def check_db_status(title, artist):
    """Comprueba si una canción ya existe en bibliotecaMusical (en librería o en descubiertas)"""
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
    except Exception:
        return None

def sync_aceptadas_to_libreria():
    """Detecta si una canción aceptada ya fue descargada e indexada en Navidrome para moverla a librería"""
    playlist_id = get_target_playlist_id()
    playlist_tracks = get_playlist_track_ids(playlist_id) if playlist_id else set()
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, title, artist, preview_url FROM canciones_descubiertas WHERE estado = 'aceptada'")
    for row in cursor.fetchall():
        in_nav, nav_id = search_in_navidrome(row['title'], row['artist'])
        if in_nav:
            print(f"✓ Canción descargada detectada: {row['title']}. Añadiendo a playlist...")
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

def sync_playlist_faltantes():
    """Comprueba canciones en librería que falten por marcar como 'en playlist'"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, title, artist, navidrome_id FROM canciones_libreria WHERE en_playlist = FALSE AND ignorar_playlist = FALSE")
        faltan = cursor.fetchall()
        
        playlist_id = get_target_playlist_id()
        playlist_tracks = get_playlist_track_ids(playlist_id) if playlist_id else set()
        
        for row in faltan:
            nav_id = row['navidrome_id']
            if not nav_id:
                in_nav, nav_id = search_in_navidrome(row['title'], row['artist'])
                if nav_id:
                    cursor.execute("UPDATE canciones_libreria SET navidrome_id = %s WHERE id = %s", (nav_id, row['id']))
            
            if nav_id and playlist_id:
                if nav_id in playlist_tracks:
                    cursor.execute("UPDATE canciones_libreria SET en_playlist = TRUE WHERE id = %s", (row['id'],))
                    
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error sincronizando faltantes: {e}")

def audit_single_song(row, playlist_tracks):
    """Audita una canción de canciones_libreria contra Navidrome"""
    song_id = row['id']
    nav_id = row.get('navidrome_id')
    title = row['title']
    artist = row['artist']
    preview = row.get('preview_url')
    was_in_playlist = bool(row.get('en_playlist'))
    
    # 1. Comprobar si el nav_id actual existe y sigue vivo en Navidrome
    exists = False
    if nav_id:
        song_info = get_navidrome_song(nav_id)
        if song_info:
            exists = True
            
    if exists:
        in_playlist = nav_id in playlist_tracks
        return {
            'id': song_id,
            'estado_archivo': 'ok',
            'nuevo_navidrome_id': None,
            'nuevo_titulo': None,
            'nuevo_artista': None,
            'en_playlist': in_playlist,
            'preview_url': preview
        }
        
    # 2. Si no existe o no tenía nav_id, buscamos si cambió de nombre o ID en Navidrome (Renombrada)
    found, new_song = find_song_in_navidrome(title, artist)
    if found and new_song:
        new_id = new_song.get('id')
        new_title = new_song.get('title')
        new_artist = new_song.get('artist')
        in_playlist = new_id in playlist_tracks
        return {
            'id': song_id,
            'estado_archivo': 'renombrada',
            'nuevo_navidrome_id': new_id,
            'nuevo_titulo': new_title,
            'nuevo_artista': new_artist,
            'en_playlist': in_playlist or was_in_playlist,
            'preview_url': preview
        }
    else:
        # 3. Desaparecida de disco
        if not preview:
            preview = get_itunes_preview(title, artist)
        return {
            'id': song_id,
            'estado_archivo': 'desaparecida',
            'nuevo_navidrome_id': None,
            'nuevo_titulo': None,
            'nuevo_artista': None,
            'en_playlist': was_in_playlist,
            'preview_url': preview
        }

def audit_library():
    """Ejecuta una auditoría completa de la librería contra Navidrome en hilos paralelos"""
    print("🔍 [Auditoría] Comprobando biblioteca contra Navidrome...")
    try:
        playlist_id = get_target_playlist_id()
        playlist_tracks = get_playlist_track_ids(playlist_id) if playlist_id else set()
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, title, artist, navidrome_id, en_playlist, preview_url FROM canciones_libreria")
        songs = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not songs:
            print("ℹ️ [Auditoría] No hay canciones en canciones_libreria.")
            return
            
        results = []
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(audit_single_song, s, playlist_tracks) for s in songs]
            for f in futures:
                try:
                    res = f.result()
                    if res:
                        results.append(res)
                except Exception as ex:
                    print(f"Error procesando hilo de auditoria: {ex}")
                    
        conn = get_db_connection()
        cursor = conn.cursor()
        for r in results:
            cursor.execute("""
                UPDATE canciones_libreria 
                SET estado_archivo = %s,
                    nuevo_navidrome_id = %s,
                    nuevo_titulo = %s,
                    nuevo_artista = %s,
                    en_playlist = %s,
                    preview_url = COALESCE(%s, preview_url),
                    last_checked = NOW()
                WHERE id = %s
            """, (
                r['estado_archivo'],
                r['nuevo_navidrome_id'],
                r['nuevo_titulo'],
                r['nuevo_artista'],
                r['en_playlist'],
                r['preview_url'],
                r['id']
            ))
        conn.commit()
        cursor.close()
        conn.close()
        print(f"✓ [Auditoría] Finalizada con éxito. Canciones analizadas: {len(results)}")
    except Exception as e:
        print(f"✗ [Auditoría] Error general en auditoria: {e}")
