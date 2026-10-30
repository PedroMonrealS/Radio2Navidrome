from database import get_stats_db_connection

INTERVAL_MAP = {
    'today': '1 DAY',
    'week': '1 WEEK',
    'month': '1 MONTH',
    'year': '1 YEAR'
}

def get_stats(range_val='all'):
    """Obtiene conteo de canciones, artistas y escuchas en el periodo especificado"""
    where_clause = ""
    if range_val and range_val != 'all':
        interval = INTERVAL_MAP.get(range_val, '1 YEAR')
        where_clause = f"WHERE reproducido_en >= DATE_SUB(NOW(), INTERVAL {interval})"

    conn = get_stats_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(f"""
        SELECT 
            (SELECT COUNT(*) FROM canciones) as songs_count,
            (SELECT COUNT(*) FROM autores) as artists_count,
            (SELECT COUNT(*) FROM escuchas {where_clause}) as listens_count
    """)
    stats = cursor.fetchone() or {}
    cursor.close()
    conn.close()
    return {
        "songs_count": int(stats.get('songs_count', 0)),
        "artists_count": int(stats.get('artists_count', 0)),
        "listens_count": int(stats.get('listens_count', 0))
    }

def get_top_artists(range_val='all', limit=15):
    """Obtiene los artistas más reproducidos en el periodo"""
    where_clause = ""
    if range_val and range_val != 'all':
        interval = INTERVAL_MAP.get(range_val, '1 YEAR')
        where_clause = f"AND e.reproducido_en >= DATE_SUB(NOW(), INTERVAL {interval})"

    conn = get_stats_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(f"""
        SELECT 
            a.nombre,
            COUNT(e.id) as total_reproducciones,
            MAX(c.imagen_url) as imagen_url
        FROM autores a
        JOIN cancion_autor ca ON a.spotify_id = ca.autor_id
        JOIN canciones c ON ca.cancion_id = c.spotify_id
        JOIN escuchas e ON c.spotify_id = e.spotify_id_cancion
        WHERE 1=1 {where_clause}
        GROUP BY a.spotify_id, a.nombre
        ORDER BY total_reproducciones DESC
        LIMIT %s;
    """, (limit,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def get_top_albums(range_val='all', limit=10):
    """Obtiene los álbumes más reproducidos en el periodo"""
    where_clause = ""
    if range_val and range_val != 'all':
        interval = INTERVAL_MAP.get(range_val, '1 YEAR')
        where_clause = f"AND e.reproducido_en >= DATE_SUB(NOW(), INTERVAL {interval})"

    conn = get_stats_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(f"""
        SELECT 
            c.album_nombre,
            MAX(c.imagen_url) as imagen_url,
            COUNT(e.id) as total_reproducciones,
            MAX(a.nombre) as artista_principal
        FROM canciones c
        JOIN escuchas e ON c.spotify_id = e.spotify_id_cancion
        JOIN cancion_autor ca ON c.spotify_id = ca.cancion_id
        JOIN autores a ON ca.autor_id = a.spotify_id
        WHERE 1=1 {where_clause}
        GROUP BY c.album_nombre
        ORDER BY total_reproducciones DESC
        LIMIT %s;
    """, (limit,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def get_songs(range_val='all'):
    """Obtiene la lista completa de canciones con sus reproducciones en el periodo"""
    join_condition = ""
    if range_val and range_val != 'all':
        interval = INTERVAL_MAP.get(range_val, '1 YEAR')
        join_condition = f"AND CAST(e.reproducido_en AS DATETIME) >= DATE_SUB(NOW(), INTERVAL {interval})"

    conn = get_stats_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(f"""
        SELECT 
            c.spotify_id,
            c.nombre AS nombre_cancion,
            c.album_nombre,
            c.imagen_url,
            GROUP_CONCAT(DISTINCT a.nombre SEPARATOR ', ') AS artistas,
            COUNT(e.id) AS total_reproducciones
        FROM canciones c
        LEFT JOIN cancion_autor ca ON c.spotify_id = ca.cancion_id
        LEFT JOIN autores a ON ca.autor_id = a.spotify_id
        LEFT JOIN escuchas e ON c.spotify_id = e.spotify_id_cancion {join_condition}
        GROUP BY c.spotify_id, c.nombre, c.album_nombre, c.imagen_url
        ORDER BY total_reproducciones DESC;
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def get_history(limit=50, offset=0, search=''):
    """Obtiene el historial cronológico lineal de escuchas"""
    search_condition = ""
    params = []
    if search:
        search_condition = "AND (c.nombre LIKE %s OR a.nombre LIKE %s OR c.album_nombre LIKE %s)"
        wildcard = f"%{search}%"
        params.extend([wildcard, wildcard, wildcard])

    params.extend([limit, offset])

    conn = get_stats_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(f"""
        SELECT 
            e.id,
            e.reproducido_en,
            c.spotify_id,
            c.nombre AS cancion,
            c.album_nombre,
            c.imagen_url,
            GROUP_CONCAT(DISTINCT a.nombre SEPARATOR ', ') AS artistas
        FROM escuchas e
        LEFT JOIN canciones c ON e.spotify_id_cancion = c.spotify_id
        LEFT JOIN cancion_autor ca ON c.spotify_id = ca.cancion_id
        LEFT JOIN autores a ON ca.autor_id = a.spotify_id
        WHERE 1=1 {search_condition}
        GROUP BY e.id, e.reproducido_en, c.spotify_id, c.nombre, c.album_nombre, c.imagen_url
        ORDER BY e.reproducido_en DESC, e.id DESC
        LIMIT %s OFFSET %s;
    """, tuple(params))
    rows = cursor.fetchall()
    for r in rows:
        if r.get('reproducido_en'):
            r['reproducido_en'] = r['reproducido_en'].isoformat()
    cursor.close()
    conn.close()
    return rows
