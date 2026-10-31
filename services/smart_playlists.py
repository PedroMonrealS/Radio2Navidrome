import requests
from config import NAVIDROME_URL, TARGET_PLAYLIST_NAME
from database import get_db_connection
from services.navidrome import get_navidrome_params, search_in_navidrome
from services.stats_service import get_top_songs

RADIO_DISCOVERIES_PLAYLIST = "📻 Descubrimientos de Radio"
TOP_LISTENS_PLAYLIST = "🔥 Top 50 Más Escuchados"

def get_or_create_subsonic_playlist(playlist_name):
    """Obtiene el ID de una playlist en Navidrome por nombre, o la crea si no existe"""
    params = get_navidrome_params()
    try:
        response = requests.get(f"{NAVIDROME_URL}/rest/getPlaylists.view", params=params, timeout=10)
        playlists = response.json().get('subsonic-response', {}).get('playlists', {}).get('playlist', [])
        for p in playlists:
            if p.get('name') == playlist_name:
                return p.get('id')
    except Exception as e:
        print(f"Error getPlaylists: {e}")

    # Si no existe, la crea vacía
    try:
        create_res = requests.post(f"{NAVIDROME_URL}/rest/createPlaylist.view", data=get_navidrome_params({'name': playlist_name}), timeout=10)
        pl = create_res.json().get('subsonic-response', {}).get('playlist', {})
        return pl.get('id')
    except Exception as e:
        print(f"Error creando playlist {playlist_name}: {e}")
        return None

def sync_radio_discoveries_playlist(limit=50):
    """Sincroniza en Navidrome los últimos N descubrimientos de radio presentes en la librería"""
    pid = get_or_create_subsonic_playlist(RADIO_DISCOVERIES_PLAYLIST)
    if not pid:
        return False, "No se pudo acceder o crear la playlist en Navidrome"

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT navidrome_id, title, artist 
        FROM canciones_libreria 
        WHERE navidrome_id IS NOT NULL AND navidrome_id != '' 
        ORDER BY added_at DESC, id DESC 
        LIMIT %s
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return True, "No hay canciones en canciones_libreria"

    # Enviar lista a createPlaylist con playlistId para sobreescribir la pista completa
    data = list(get_navidrome_params({'playlistId': pid, 'name': RADIO_DISCOVERIES_PLAYLIST}).items())
    for r in rows:
        data.append(('songId', r['navidrome_id']))

    try:
        res = requests.post(f"{NAVIDROME_URL}/rest/createPlaylist.view", data=data, timeout=15)
        ok = res.json().get('subsonic-response', {}).get('status') == 'ok'
        if ok:
            return True, f"Playlist '{RADIO_DISCOVERIES_PLAYLIST}' actualizada con {len(rows)} temas."
        return False, "Error al actualizar la playlist en Navidrome"
    except Exception as e:
        return False, str(e)

def sync_top_listens_playlist(limit=50):
    """Sincroniza en Navidrome las 50 canciones más escuchadas de tus estadísticas"""
    pid = get_or_create_subsonic_playlist(TOP_LISTENS_PLAYLIST)
    if not pid:
        return False, "No se pudo acceder o crear la playlist en Navidrome"

    # 1. Obtener top canciones de spotify_db
    top_songs = get_top_songs(range_val='all', limit=limit * 2) # Margen por si alguna no está en disco
    if not top_songs:
        return True, "No hay datos de escuchas"

    # 2. Mapear canciones con canciones_libreria
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT navidrome_id, title, artist FROM canciones_libreria WHERE navidrome_id IS NOT NULL AND navidrome_id != ''")
    lib_songs = cursor.fetchall()
    conn.close()

    from services.utils import clean_text
    lib_dict = {(clean_text(s['artist']), clean_text(s['title'])): s['navidrome_id'] for s in lib_songs}

    matched_nav_ids = []
    for s in top_songs:
        tit = s.get('nombre', '')
        art = s.get('artista', '')
        key = (clean_text(art), clean_text(tit))
        nav_id = lib_dict.get(key)
        if not nav_id:
            # Búsqueda directa
            found, sid = search_in_navidrome(tit, art)
            if found and sid:
                nav_id = sid
        if nav_id and nav_id not in matched_nav_ids:
            matched_nav_ids.append(nav_id)
            if len(matched_nav_ids) >= limit:
                break

    if not matched_nav_ids:
        return False, "No se encontraron canciones del Top escuchadas en tu biblioteca de Navidrome"

    data = list(get_navidrome_params({'playlistId': pid, 'name': TOP_LISTENS_PLAYLIST}).items())
    for nid in matched_nav_ids:
        data.append(('songId', nid))

    try:
        res = requests.post(f"{NAVIDROME_URL}/rest/createPlaylist.view", data=data, timeout=15)
        ok = res.json().get('subsonic-response', {}).get('status') == 'ok'
        if ok:
            return True, f"Playlist '{TOP_LISTENS_PLAYLIST}' actualizada con {len(matched_nav_ids)} temas."
        return False, "Error al actualizar la playlist en Navidrome"
    except Exception as e:
        return False, str(e)

def sync_all_smart_playlists():
    """Ejecuta la sincronización de ambas Smart Playlists"""
    r1, msg1 = sync_radio_discoveries_playlist(50)
    r2, msg2 = sync_top_listens_playlist(50)
    return {
        "success": r1 and r2,
        "radio_discoveries": {"success": r1, "message": msg1},
        "top_listens": {"success": r2, "message": msg2}
    }
