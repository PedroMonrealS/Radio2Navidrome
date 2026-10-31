import re
from database import get_db_connection

# Patterns to detect non-original track versions
RE_PAREN_VERSION = re.compile(
    r'\s*[\(\[]\s*([^()\[\]]*?\b(?:remix|rmx|mix|radio\s+edit|radio\s+mix|club\s+mix|club\s+edit|extended(?:\s+mix|\s+version)?|acoustic|ac[uú]stic[oa]|live|en\s+vivo|en\s+directo|sped\s*up|slowed|instrumental|cover|versi[oó]n|edit)\b[^()\[\]]*)\s*[\)\]]',
    re.IGNORECASE
)

RE_DASH_VERSION = re.compile(
    r'\s+[-/]\s+(.*?\b(?:remix|rmx|radio\s+edit|radio\s+mix|club\s+mix|club\s+edit|extended(?:\s+mix|\s+version)?|acoustic|ac[uú]stic[oa]|live|en\s+vivo|en\s+directo|sped\s*up|slowed|instrumental|cover|versi[oó]n|edit)\b.*)$',
    re.IGNORECASE
)

def detect_song_version(title):
    """
    Analiza si el título corresponde a una versión/remix/live/edit y extrae el título original limpio.
    Retorna: (is_version: bool, version_tag: str, clean_original_title: str)
    """
    if not title:
        return False, "", ""
    
    # Comprobar versiones entre paréntesis o corchetes: "Song (Remix)"
    m_paren = RE_PAREN_VERSION.search(title)
    if m_paren:
        tag = m_paren.group(1).strip()
        clean = RE_PAREN_VERSION.sub('', title).strip(' -/()[]')
        return True, tag, clean
        
    # Comprobar sufijos tras guión: "Song - Club Mix"
    m_dash = RE_DASH_VERSION.search(title)
    if m_dash:
        tag = m_dash.group(1).strip()
        clean = RE_DASH_VERSION.sub('', title).strip(' -/()[]')
        return True, tag, clean
        
    return False, "", title.strip()

def enrich_songs_with_version_info(songs_list, conn=None):
    """
    Enriquece cada canción con:
    - is_version (bool)
    - version_tag (str)
    - original_title (str)
    - original_in_library (bool)
    - library_match_title (str)
    """
    if not songs_list:
        return songs_list
        
    # Obtener catálogo de biblioteca para comprobaciones rápidas
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
        
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, artist, title, en_playlist FROM canciones_libreria")
        lib_items = cursor.fetchall()
        
        # Mapeo rápido: (artist_lower, clean_title_lower) -> item
        # También mapa por artista para búsqueda flexible
        artist_map = {}
        for item in lib_items:
            a_norm = item['artist'].lower().strip()
            t_norm = item['title'].lower().strip()
            if a_norm not in artist_map:
                artist_map[a_norm] = []
            artist_map[a_norm].append((t_norm, item['title']))
            
        for s in songs_list:
            title = s.get('title', '')
            artist = s.get('artist', '')
            is_ver, ver_tag, clean_title = detect_song_version(title)
            
            s['is_version'] = is_ver
            s['version_tag'] = ver_tag
            s['original_title'] = clean_title
            s['original_in_library'] = False
            s['library_match_title'] = ""
            
            # Si es una versión, buscar si el original ya existe en la biblioteca
            if is_ver and clean_title:
                a_norm = artist.lower().strip()
                clean_norm = clean_title.lower().strip()
                
                # Buscar canciones del mismo artista
                candidates = artist_map.get(a_norm, [])
                for t_norm, raw_title in candidates:
                    # Coincidencia exacta o contenida del título original
                    if t_norm == clean_norm or clean_norm in t_norm or t_norm in clean_norm:
                        s['original_in_library'] = True
                        s['library_match_title'] = raw_title
                        break
    finally:
        if close_conn and conn:
            conn.close()
            
    return songs_list
