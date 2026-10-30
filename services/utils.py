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
