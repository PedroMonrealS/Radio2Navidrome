import re
import unicodedata
import requests
from thefuzz import fuzz
from config import FUZZY_THRESHOLD

def clean_text(text):
    """Limpia texto quitando acentos, caracteres especiales y paréntesis"""
    if not text:
        return ""
    text = text.lower()
    # Eliminar acentos y diacríticos latinos
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    # Eliminar paréntesis y su contenido
    text = re.sub(r'[\(\[].*?[\)\]]', '', text)
    # Reemplazar no alfanuméricos por espacios
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    return " ".join(text.split())

def is_same_song(song1_title, song1_artist, song2_title, song2_artist):
    """Compara si dos canciones son la misma usando lógica fuzzy robusta"""
    c_title1, c_artist1 = clean_text(song1_title), clean_text(song1_artist)
    c_title2, c_artist2 = clean_text(song2_title), clean_text(song2_artist)
    score_title = fuzz.token_set_ratio(c_title1, c_title2)
    score_artist = fuzz.token_set_ratio(c_artist1, c_artist2)
    score_combo = fuzz.token_set_ratio(f"{c_artist1} {c_title1}", f"{c_artist2} {c_title2}")
    return score_combo >= FUZZY_THRESHOLD or (score_title >= FUZZY_THRESHOLD and score_artist >= FUZZY_THRESHOLD)

def get_itunes_preview(title, artist):
    """Busca en el API de iTunes una vista previa de audio de 30 segundos"""
    try:
        term = f"{artist} {title}"
        res = requests.get(
            "https://itunes.apple.com/search",
            params={"term": term, "entity": "song", "limit": 1},
            timeout=5
        )
        data = res.json()
        if data.get('resultCount', 0) > 0:
            return data['results'][0].get('previewUrl', '')
    except Exception:
        pass
    return None

def is_radio_promo_or_jingle(title, artist, station=''):
    """Detecta si un evento emitido en radio es una promo, cuña publicitaria, jingle o noticias"""
    t = (title or '').lower().strip()
    a = (artist or '').lower().strip()
    s = (station or '').lower().strip()
    
    # 1. Palabras clave explícitas de cuñas y noticias
    keywords = [
        'noticia', 'variedad musical', 'la mejor variedad', 'megakiss',
        'boletin', 'boletín', 'informativo', 'indi inicio', 'indi fin',
        'jingle', 'publicidad', 'patrocinio', 'sintonía', 'sintonia',
        'despertador', 'buenos dias', 'buenos días'
    ]
    for kw in keywords:
        if kw in t or kw in a:
            return True
            
    # 2. Nombre de la emisora como artista o título
    station_names = ['cadena 100', 'kiss fm', 'los40', 'los 40', 'cadena dial', 'dial', 'cope', 'ser', 'onda cero']
    if s:
        station_names.append(s)
        
    for sn in station_names:
        if a == sn or t == sn:
            return True
            
    # 3. Presentadores de bloques informativos de radio
    if a.startswith('con ') and ('noticia' in t or 'kiss' in t or 'cadena' in t or 'los40' in t):
        return True
    if t.startswith('con ') and ('noticia' in a or 'kiss' in a or 'cadena' in a or 'los40' in a):
        return True
        
    return False
