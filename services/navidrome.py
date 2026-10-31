import random
import string
import hashlib
import time
from collections import defaultdict
import requests
from config import NAVIDROME_URL, NAVIDROME_USER, NAVIDROME_PASS, TARGET_PLAYLIST_NAME
from services.utils import clean_text, is_same_song

_duplicates_cache = {
    'time': 0,
    'data': None
}

def invalidate_duplicates_cache():
    """Invalida el caché de canciones duplicadas en playlist"""
    global _duplicates_cache
    _duplicates_cache['time'] = 0
    _duplicates_cache['data'] = None

def get_navidrome_params(extra_params=None):
    """Genera los parámetros de autenticación Subsonic requeridos por Navidrome"""
    salt = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    token = hashlib.md5((NAVIDROME_PASS + salt).encode('utf-8')).hexdigest()
    params = {
        'u': NAVIDROME_USER,
        't': token,
        's': salt,
        'v': '1.16.1',
        'c': 'radioSync',
        'f': 'json'
    }
    if extra_params:
        params.update(extra_params)
    return params

def search_in_navidrome(title, artist):
    """Busca si una canción existe en Navidrome. Devuelve (en_libreria, navidrome_id)"""
    clean_query = f"{clean_text(artist)} {clean_text(title)}"
    params = get_navidrome_params({'query': clean_query})
    try:
        response = requests.get(f"{NAVIDROME_URL}/rest/search3.view", params=params, timeout=10)
        response.raise_for_status()
        songs = response.json().get('subsonic-response', {}).get('searchResult3', {}).get('song', [])
        for s in songs:
            if is_same_song(title, artist, s.get('title', ''), s.get('artist', '')):
                return True, s.get('id')
    except Exception as e:
        print(f"Error Navidrome search: {e}")
    return False, None

def get_target_playlist_id():
    """Obtiene el ID de la playlist objetivo configurada (ej. 'Canciones que te gustan')"""
    params = get_navidrome_params()
    try:
        response = requests.get(f"{NAVIDROME_URL}/rest/getPlaylists.view", params=params, timeout=10)
        playlists = response.json().get('subsonic-response', {}).get('playlists', {}).get('playlist', [])
        for p in playlists:
            if p.get('name') == TARGET_PLAYLIST_NAME:
                return p.get('id')
    except Exception as e:
        print(f"Error Navidrome getPlaylists: {e}")
    return None

def get_playlist_track_ids(playlist_id):
    """Obtiene el set de IDs de canciones que están dentro de una playlist"""
    if not playlist_id:
        return set()
    params = get_navidrome_params({'id': playlist_id})
    try:
        response = requests.get(f"{NAVIDROME_URL}/rest/getPlaylist.view", params=params, timeout=10)
        tracks = response.json().get('subsonic-response', {}).get('playlist', {}).get('entry', [])
        return {t.get('id') for t in tracks}
    except Exception as e:
        print(f"Error Navidrome getPlaylist: {e}")
    return set()

def add_song_to_playlist(playlist_id, song_id):
    """Añade una canción por su ID a una playlist en Navidrome, evitando duplicados si ya existe"""
    if not playlist_id or not song_id:
        return False
    current_tracks = get_playlist_track_ids(playlist_id)
    if song_id in current_tracks:
        return True
    params = get_navidrome_params({'playlistId': playlist_id, 'songIdToAdd': song_id})
    try:
        res = requests.post(f"{NAVIDROME_URL}/rest/updatePlaylist.view", data=params, timeout=10)
        if res.status_code == 200:
            invalidate_duplicates_cache()
            return True
        return False
    except Exception:
        return False

def star_song_in_navidrome(song_id):
    """Marca como favorita (estrella) una canción en Navidrome"""
    if not song_id:
        return False
    params = get_navidrome_params({'id': song_id})
    try:
        res = requests.get(f"{NAVIDROME_URL}/rest/star.view", params=params, timeout=10)
        return res.status_code == 200
    except Exception:
        return False

def get_navidrome_song(song_id):
    """Comprueba si un ID específico existe y sigue vivo en Navidrome. Devuelve dict o None"""
    if not song_id:
        return None
    params = get_navidrome_params({'id': song_id})
    try:
        res = requests.get(f"{NAVIDROME_URL}/rest/getSong.view", params=params, timeout=8)
        if res.status_code == 200:
            sub = res.json().get('subsonic-response', {})
            if sub.get('status') == 'ok' and 'song' in sub:
                return sub.get('song')
    except Exception as e:
        print(f"Error comprobando cancion {song_id} en Navidrome: {e}")
    return None

def find_song_in_navidrome(title, artist):
    """Busca en Navidrome y devuelve (found, song_dict) con información de la pista encontrada"""
    clean_query = f"{clean_text(artist)} {clean_text(title)}"
    params = get_navidrome_params({'query': clean_query})
    try:
        response = requests.get(f"{NAVIDROME_URL}/rest/search3.view", params=params, timeout=10)
        response.raise_for_status()
        songs = response.json().get('subsonic-response', {}).get('searchResult3', {}).get('song', [])
        for s in songs:
            if is_same_song(title, artist, s.get('title', ''), s.get('artist', '')):
                return True, s
    except Exception as e:
        print(f"Error Navidrome search: {e}")
    return False, None

def remove_song_from_playlist(playlist_id, song_id):
    """Elimina una canción de una playlist por su ID en Navidrome usando songIndexToRemove"""
    if not playlist_id or not song_id:
        return True
    try:
        params = get_navidrome_params({'id': playlist_id})
        res = requests.get(f"{NAVIDROME_URL}/rest/getPlaylist.view", params=params, timeout=10)
        tracks = res.json().get('subsonic-response', {}).get('playlist', {}).get('entry', [])
        
        matching_indices = [i for i, t in enumerate(tracks) if t.get('id') == song_id]
        if not matching_indices:
            return True
            
        for idx in sorted(matching_indices, reverse=True):
            del_params = get_navidrome_params({'playlistId': playlist_id, 'songIndexToRemove': idx})
            requests.get(f"{NAVIDROME_URL}/rest/updatePlaylist.view", params=del_params, timeout=10)
            time.sleep(0.05)
        invalidate_duplicates_cache()
        return True
    except Exception as e:
        print(f"Error eliminando cancion {song_id} de playlist {playlist_id}: {e}")
        return False

def get_playlist_duplicates(force_refresh=False):
    """Detecta canciones repetidas dentro de la playlist objetivo"""
    global _duplicates_cache
    now = time.time()
    if not force_refresh and _duplicates_cache['data'] and (now - _duplicates_cache['time'] < 20):
        return _duplicates_cache['data']

    pid = get_target_playlist_id()
    if not pid:
        return {'duplicates': [], 'total_duplicates': 0, 'total_redundant': 0, 'playlist_name': TARGET_PLAYLIST_NAME}

    try:
        res = requests.get(f"{NAVIDROME_URL}/rest/getPlaylist.view", params=get_navidrome_params({'id': pid}), timeout=15)
        playlist = res.json().get('subsonic-response', {}).get('playlist', {})
        entries = playlist.get('entry', [])
    except Exception as e:
        print(f"Error al obtener playlist para duplicados: {e}")
        return {'duplicates': [], 'total_duplicates': 0, 'total_redundant': 0, 'playlist_name': TARGET_PLAYLIST_NAME}

    # Indexar previews de canciones_libreria
    previews = {}
    try:
        from database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT title, artist, navidrome_id, preview_url FROM canciones_libreria WHERE preview_url IS NOT NULL AND preview_url != ''")
        for r in cursor.fetchall():
            if r.get('navidrome_id'):
                previews[r['navidrome_id']] = r['preview_url']
            previews[(clean_text(r['artist']), clean_text(r['title']))] = r['preview_url']
        conn.close()
    except Exception as e:
        print(f"Aviso obteniendo previews para duplicados: {e}")

    by_key = defaultdict(list)
    for idx, track in enumerate(entries):
        c_art = clean_text(track.get('artist', ''))
        c_tit = clean_text(track.get('title', ''))
        key = (c_art, c_tit) if c_art and c_tit else track.get('id')
        by_key[key].append((idx, track))

    dups = []
    total_redundant = 0
    for key, items in by_key.items():
        if len(items) > 1:
            total_redundant += len(items) - 1
            first_idx, first_track = items[0]
            c_art = clean_text(first_track.get('artist', ''))
            c_tit = clean_text(first_track.get('title', ''))
            p_url = previews.get(first_track.get('id')) or previews.get((c_art, c_tit))
            dups.append({
                'title': first_track.get('title'),
                'artist': first_track.get('artist'),
                'navidrome_id': first_track.get('id'),
                'count': len(items),
                'redundant': len(items) - 1,
                'albums': list(dict.fromkeys(t.get('album', '') for _, t in items if t.get('album'))),
                'indices_to_remove': [idx for idx, _ in items[1:]],
                'preview_url': p_url
            })

    dups.sort(key=lambda x: (x['count'], x['artist']), reverse=True)
    result = {
        'duplicates': dups,
        'total_duplicates': len(dups),
        'total_redundant': total_redundant,
        'playlist_name': playlist.get('name', TARGET_PLAYLIST_NAME)
    }
    _duplicates_cache['time'] = now
    _duplicates_cache['data'] = result
    return result

def remove_song_duplicates(artist, title):
    """Elimina las copias duplicadas de una canción específica en la playlist, conservando la primera"""
    pid = get_target_playlist_id()
    if not pid:
        return {'success': False, 'error': 'No se encontró la playlist objetivo'}
    
    try:
        res = requests.get(f"{NAVIDROME_URL}/rest/getPlaylist.view", params=get_navidrome_params({'id': pid}), timeout=15)
        entries = res.json().get('subsonic-response', {}).get('playlist', {}).get('entry', [])
        
        target_key = (clean_text(artist), clean_text(title))
        matching_indices = [
            idx for idx, t in enumerate(entries)
            if (clean_text(t.get('artist', '')), clean_text(t.get('title', ''))) == target_key
        ]
        
        if len(matching_indices) <= 1:
            return {'success': True, 'removed_count': 0}
            
        indices_to_remove = sorted(matching_indices[1:], reverse=True)
        del_data = list(get_navidrome_params({'playlistId': pid}).items())
        for idx in indices_to_remove:
            del_data.append(('songIndexToRemove', idx))
            
        res_del = requests.post(f"{NAVIDROME_URL}/rest/updatePlaylist.view", data=del_data, timeout=15)
        invalidate_duplicates_cache()
        return {'success': res_del.status_code == 200, 'removed_count': len(indices_to_remove)}
    except Exception as e:
        print(f"Error remove_song_duplicates: {e}")
        return {'success': False, 'error': str(e)}

def remove_all_duplicates_from_playlist():
    """Elimina TODAS las copias redundantes de la playlist a la vez en lotes descendentes"""
    pid = get_target_playlist_id()
    if not pid:
        return {'success': False, 'error': 'No se encontró la playlist objetivo'}
        
    try:
        res = requests.get(f"{NAVIDROME_URL}/rest/getPlaylist.view", params=get_navidrome_params({'id': pid}), timeout=15)
        entries = res.json().get('subsonic-response', {}).get('playlist', {}).get('entry', [])
        
        seen = set()
        indices_to_remove = []
        for idx, track in enumerate(entries):
            c_art = clean_text(track.get('artist', ''))
            c_tit = clean_text(track.get('title', ''))
            key = (c_art, c_tit) if c_art and c_tit else track.get('id')
            if key in seen:
                indices_to_remove.append(idx)
            else:
                seen.add(key)
                
        if not indices_to_remove:
            invalidate_duplicates_cache()
            return {'success': True, 'removed_count': 0}
            
        indices_descending = sorted(indices_to_remove, reverse=True)
        chunk_size = 50
        for i in range(0, len(indices_descending), chunk_size):
            chunk = indices_descending[i:i + chunk_size]
            del_data = list(get_navidrome_params({'playlistId': pid}).items())
            for idx in chunk:
                del_data.append(('songIndexToRemove', idx))
            requests.post(f"{NAVIDROME_URL}/rest/updatePlaylist.view", data=del_data, timeout=15)
            time.sleep(0.04)
            
        invalidate_duplicates_cache()
        return {'success': True, 'removed_count': len(indices_to_remove)}
    except Exception as e:
        print(f"Error remove_all_duplicates_from_playlist: {e}")
        return {'success': False, 'error': str(e)}
