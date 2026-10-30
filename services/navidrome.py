import random
import string
import hashlib
import time
import requests
from config import NAVIDROME_URL, NAVIDROME_USER, NAVIDROME_PASS, TARGET_PLAYLIST_NAME
from services.utils import clean_text, is_same_song

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
    """Añade una canción por su ID a una playlist en Navidrome"""
    if not playlist_id or not song_id:
        return False
    params = get_navidrome_params({'playlistId': playlist_id, 'songIdToAdd': song_id})
    try:
        res = requests.get(f"{NAVIDROME_URL}/rest/updatePlaylist.view", params=params, timeout=10)
        return res.status_code == 200
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
        return True
    except Exception as e:
        print(f"Error eliminando cancion {song_id} de playlist {playlist_id}: {e}")
        return False
