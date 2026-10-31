import urllib.parse
from database import get_stats_db_connection

INTERVAL_MAP = {
    'today': '1 DAY',
    'week': '7 DAY',
    'month': '1 MONTH',
    'year': '1 YEAR'
}

def get_stats(range_val='today'):
    """Obtiene el resumen de conteos de canciones, artistas y escuchas según el rango"""
    where_clause = ""
    if range_val and range_val != 'all':
        interval = INTERVAL_MAP.get(range_val, '1 DAY')
        where_clause = f"WHERE e.reproducido_en >= DATE_SUB(NOW(), INTERVAL {interval})"

    conn = get_stats_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(f"""
        SELECT 
            (SELECT COUNT(*) FROM canciones) as songs_count,
            (SELECT COUNT(*) FROM autores) as artists_count,
            COUNT(e.id) as listens_count
        FROM escuchas e
        {where_clause};
    """)
    stats = cursor.fetchone() or {}
    cursor.close()
    conn.close()

    return {
        "songs_count": int(stats.get('songs_count', 0)),
        "artists_count": int(stats.get('artists_count', 0)),
        "listens_count": int(stats.get('listens_count', 0))
    }

def get_period_comparison(range_val='week'):
    """Calcula la comparativa de tendencias respecto al periodo anterior equivalente"""
    if range_val not in ['today', 'week', 'month', 'year']:
        return {"has_comparison": False}

    intervals = {
        'today': (1, 2, 'ayer'),
        'week': (7, 14, 'la semana anterior'),
        'month': (30, 60, 'el mes anterior'),
        'year': (365, 730, 'el año anterior')
    }

    cur_days, prev_days, comp_label = intervals[range_val]

    conn = get_stats_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = f"""
        SELECT 
            COUNT(CASE WHEN e.reproducido_en >= DATE_SUB(NOW(), INTERVAL {cur_days} DAY) THEN 1 END) as cur_listens,
            COUNT(CASE WHEN e.reproducido_en >= DATE_SUB(NOW(), INTERVAL {prev_days} DAY) AND e.reproducido_en < DATE_SUB(NOW(), INTERVAL {cur_days} DAY) THEN 1 END) as prev_listens,
            COUNT(DISTINCT CASE WHEN e.reproducido_en >= DATE_SUB(NOW(), INTERVAL {cur_days} DAY) THEN e.spotify_id_cancion END) as cur_songs,
            COUNT(DISTINCT CASE WHEN e.reproducido_en >= DATE_SUB(NOW(), INTERVAL {prev_days} DAY) AND e.reproducido_en < DATE_SUB(NOW(), INTERVAL {cur_days} DAY) THEN e.spotify_id_cancion END) as prev_songs
        FROM escuchas e
        WHERE e.reproducido_en >= DATE_SUB(NOW(), INTERVAL {prev_days} DAY);
    """
    cursor.execute(query)
    row = cursor.fetchone() or {}

    cur_listens = int(row.get('cur_listens', 0))
    prev_listens = int(row.get('prev_listens', 0))
    cur_songs = int(row.get('cur_songs', 0))
    prev_songs = int(row.get('prev_songs', 0))

    if prev_listens > 0:
        listens_pct = round(((cur_listens - prev_listens) / prev_listens) * 100, 1)
    else:
        listens_pct = 100.0 if cur_listens > 0 else 0.0

    if prev_songs > 0:
        songs_pct = round(((cur_songs - prev_songs) / prev_songs) * 100, 1)
    else:
        songs_pct = 100.0 if cur_songs > 0 else 0.0

    rising_query = f"""
        SELECT * FROM (
            SELECT 
                a.nombre,
                COUNT(CASE WHEN e.reproducido_en >= DATE_SUB(NOW(), INTERVAL {cur_days} DAY) THEN 1 END) as cur_count,
                COUNT(CASE WHEN e.reproducido_en >= DATE_SUB(NOW(), INTERVAL {prev_days} DAY) AND e.reproducido_en < DATE_SUB(NOW(), INTERVAL {cur_days} DAY) THEN 1 END) as prev_count
            FROM escuchas e
            JOIN cancion_autor ca ON e.spotify_id_cancion = ca.cancion_id
            JOIN autores a ON ca.autor_id = a.spotify_id
            WHERE e.reproducido_en >= DATE_SUB(NOW(), INTERVAL {prev_days} DAY)
            GROUP BY a.spotify_id, a.nombre
        ) sub
        WHERE cur_count > prev_count
        ORDER BY (cur_count - prev_count) DESC
        LIMIT 1;
    """
    cursor.execute(rising_query)
    top_rising_row = cursor.fetchone()
    top_rising = None
    if top_rising_row:
        diff = top_rising_row['cur_count'] - top_rising_row['prev_count']
        top_rising = {
            "nombre": top_rising_row['nombre'],
            "crecimiento": diff,
            "cur_count": top_rising_row['cur_count']
        }

    cursor.close()
    conn.close()

    return {
        "has_comparison": True,
        "comp_label": comp_label,
        "cur_listens": cur_listens,
        "prev_listens": prev_listens,
        "listens_pct": listens_pct,
        "cur_songs": cur_songs,
        "prev_songs": prev_songs,
        "songs_pct": songs_pct,
        "top_rising": top_rising
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

def get_top_songs(range_val='all', limit=15):
    """Obtiene las canciones más reproducidas en el periodo"""
    where_clause = ""
    if range_val and range_val != 'all':
        interval = INTERVAL_MAP.get(range_val, '1 YEAR')
        where_clause = f"AND e.reproducido_en >= DATE_SUB(NOW(), INTERVAL {interval})"

    conn = get_stats_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(f"""
        SELECT 
            c.spotify_id,
            c.nombre,
            c.album_nombre,
            c.imagen_url,
            GROUP_CONCAT(DISTINCT a.nombre SEPARATOR ', ') as artista,
            COUNT(e.id) as total_reproducciones
        FROM canciones c
        JOIN escuchas e ON c.spotify_id = e.spotify_id_cancion
        LEFT JOIN cancion_autor ca ON c.spotify_id = ca.cancion_id
        LEFT JOIN autores a ON ca.autor_id = a.spotify_id
        WHERE 1=1 {where_clause}
        GROUP BY c.spotify_id, c.nombre, c.album_nombre, c.imagen_url
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
            c.imagen_url,
            COUNT(e.id) as total_reproducciones,
            (
                SELECT a2.nombre 
                FROM autores a2
                JOIN cancion_autor ca2 ON a2.spotify_id = ca2.autor_id
                WHERE ca2.cancion_id = c.spotify_id
                LIMIT 1
            ) as artista_principal
        FROM canciones c
        JOIN escuchas e ON c.spotify_id = e.spotify_id_cancion
        WHERE 1=1 {where_clause}
        GROUP BY c.album_nombre, c.imagen_url, c.spotify_id
        ORDER BY total_reproducciones DESC
        LIMIT %s;
    """, (limit,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def get_songs(page=1, per_page=20, search=""):
    """Explorador de canciones con paginación y filtro de búsqueda"""
    offset = (page - 1) * per_page
    search_condition = ""
    params = []
    if search:
        search_condition = "AND (c.nombre LIKE %s OR a.nombre LIKE %s OR c.album_nombre LIKE %s)"
        term = f"%{search}%"
        params = [term, term, term]

    conn = get_stats_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(f"""
        SELECT 
            c.spotify_id,
            c.nombre,
            c.album_nombre,
            c.imagen_url,
            GROUP_CONCAT(DISTINCT a.nombre SEPARATOR ', ') as artistas,
            COUNT(e.id) as reproducciones
        FROM canciones c
        LEFT JOIN cancion_autor ca ON c.spotify_id = ca.cancion_id
        LEFT JOIN autores a ON ca.autor_id = a.spotify_id
        LEFT JOIN escuchas e ON c.spotify_id = e.spotify_id_cancion
        WHERE 1=1 {search_condition}
        GROUP BY c.spotify_id, c.nombre, c.album_nombre, c.imagen_url
        ORDER BY reproducciones DESC
        LIMIT %s OFFSET %s;
    """, tuple(params + [per_page, offset]))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def get_history(limit=30, offset=0, search=""):
    """Obtiene el historial de escuchas en orden cronológico inverso (Lineal)"""
    search_condition = ""
    params = []
    if search:
        search_condition = "AND (c.nombre LIKE %s OR a.nombre LIKE %s OR c.album_nombre LIKE %s)"
        term = f"%{search}%"
        params = [term, term, term]

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

def get_wrapped_data():
    """Genera todas las métricas procesadas para la experiencia interactiva Music Wrapped con proxy CORS seguro"""
    conn = get_stats_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    def proxy_url(u):
        if u and (u.startswith('http://') or u.startswith('https://')):
            return f"/api/proxy-image?url={urllib.parse.quote(u)}"
        return u or "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=200"

    # 1. Totales y Volumen
    cursor.execute("""
        SELECT 
            COUNT(*) as total_escuchas,
            COUNT(DISTINCT spotify_id_cancion) as canciones_unicas
        FROM escuchas;
    """)
    res_totales = cursor.fetchone() or {"total_escuchas": 0, "canciones_unicas": 0}
    total_escuchas = int(res_totales.get("total_escuchas", 0))
    canciones_unicas = int(res_totales.get("canciones_unicas", 0))
    
    total_minutos = int(total_escuchas * 3.4)
    total_horas = round(total_minutos / 60, 1)
    dias_continuos = round(total_horas / 24, 1)
    
    cursor.execute("""
        SELECT COUNT(DISTINCT a.spotify_id) as artistas_unicos
        FROM escuchas e
        JOIN canciones c ON e.spotify_id_cancion = c.spotify_id
        JOIN cancion_autor ca ON c.spotify_id = ca.cancion_id
        JOIN autores a ON ca.autor_id = a.spotify_id;
    """)
    res_art = cursor.fetchone() or {"artistas_unicos": 0}
    artistas_unicos = int(res_art.get("artistas_unicos", 0))
    
    # 2. Canción Top 1 (Bucle)
    cursor.execute("""
        SELECT 
            c.nombre as cancion,
            c.album_nombre,
            c.imagen_url,
            GROUP_CONCAT(DISTINCT a.nombre SEPARATOR ', ') as artista,
            COUNT(e.id) as reproducciones
        FROM escuchas e
        JOIN canciones c ON e.spotify_id_cancion = c.spotify_id
        LEFT JOIN cancion_autor ca ON c.spotify_id = ca.cancion_id
        LEFT JOIN autores a ON ca.autor_id = a.spotify_id
        GROUP BY c.spotify_id, c.nombre, c.album_nombre, c.imagen_url
        ORDER BY reproducciones DESC
        LIMIT 1;
    """)
    top_song = cursor.fetchone() or {
        "cancion": "Canción Desconocida", "artista": "Artista", "imagen_url": None, "reproducciones": 0
    }
    top_song["imagen_url"] = proxy_url(top_song.get("imagen_url"))
    
    # 3. Álbum Estrella Top 1
    cursor.execute("""
        SELECT 
            c.album_nombre,
            c.imagen_url,
            COUNT(e.id) as reproducciones,
            (
                SELECT a2.nombre 
                FROM autores a2 
                JOIN cancion_autor ca2 ON a2.spotify_id = ca2.autor_id 
                WHERE ca2.cancion_id = c.spotify_id 
                LIMIT 1
            ) as artista
        FROM canciones c
        JOIN escuchas e ON c.spotify_id = e.spotify_id_cancion
        WHERE c.album_nombre IS NOT NULL AND c.album_nombre != ''
        GROUP BY c.album_nombre, c.imagen_url, c.spotify_id
        ORDER BY reproducciones DESC
        LIMIT 1;
    """)
    top_album = cursor.fetchone() or {
        "album_nombre": "Grandes Éxitos", "artista": "Varios Artistas", "imagen_url": None, "reproducciones": 0
    }
    top_album["imagen_url"] = proxy_url(top_album.get("imagen_url"))

    # 4. Top 5 Artistas
    cursor.execute("""
        SELECT 
            a.nombre,
            COUNT(e.id) as reproducciones,
            MAX(c.imagen_url) as imagen_url
        FROM autores a
        JOIN cancion_autor ca ON a.spotify_id = ca.autor_id
        JOIN canciones c ON ca.cancion_id = c.spotify_id
        JOIN escuchas e ON c.spotify_id = e.spotify_id_cancion
        GROUP BY a.spotify_id, a.nombre
        ORDER BY reproducciones DESC
        LIMIT 5;
    """)
    top_artists = cursor.fetchall()
    for a in top_artists:
        a["imagen_url"] = proxy_url(a.get("imagen_url"))
    
    # 5. Top 5 Canciones
    cursor.execute("""
        SELECT 
            c.nombre as cancion,
            c.album_nombre,
            c.imagen_url,
            GROUP_CONCAT(DISTINCT a.nombre SEPARATOR ', ') as artista,
            COUNT(e.id) as reproducciones
        FROM escuchas e
        JOIN canciones c ON e.spotify_id_cancion = c.spotify_id
        LEFT JOIN cancion_autor ca ON c.spotify_id = ca.cancion_id
        LEFT JOIN autores a ON ca.autor_id = a.spotify_id
        GROUP BY c.spotify_id, c.nombre, c.album_nombre, c.imagen_url
        ORDER BY reproducciones DESC
        LIMIT 5;
    """)
    top_songs = cursor.fetchall()
    for s in top_songs:
        s["imagen_url"] = proxy_url(s.get("imagen_url"))
    
    # 6. Pico de Actividad y Hábitos (Hora, Día y Entre semana vs Finde)
    cursor.execute("""
        SELECT HOUR(reproducido_en) as hora, COUNT(*) as c
        FROM escuchas
        GROUP BY hora
        ORDER BY c DESC
        LIMIT 1;
    """)
    row_hora = cursor.fetchone() or {"hora": 18, "c": 0}
    peak_hour = int(row_hora.get("hora", 18))
    
    cursor.execute("""
        SELECT DAYOFWEEK(reproducido_en) as dia_num, DAYNAME(reproducido_en) as dia, COUNT(*) as c
        FROM escuchas
        GROUP BY dia_num, dia
        ORDER BY c DESC
        LIMIT 1;
    """)
    row_dia = cursor.fetchone() or {"dia": "Monday", "c": 0}
    dias_traduccion = {
        "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
        "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"
    }
    peak_day = dias_traduccion.get(row_dia.get("dia", "Monday"), "Lunes")
    
    # Reparto Entre Semana vs Fin de Semana
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN DAYOFWEEK(reproducido_en) IN (1, 7) THEN 1 ELSE 0 END) as weekend_count,
            SUM(CASE WHEN DAYOFWEEK(reproducido_en) NOT IN (1, 7) THEN 1 ELSE 0 END) as weekday_count
        FROM escuchas;
    """)
    res_split = cursor.fetchone() or {"weekend_count": 0, "weekday_count": 0}
    weekend_count = int(res_split.get("weekend_count") or 0)
    weekday_count = int(res_split.get("weekday_count") or 0)
    weekend_pct = round((weekend_count / max(total_escuchas, 1)) * 100)
    weekday_pct = 100 - weekend_pct
    
    # Distribución por horas (24 horas)
    cursor.execute("""
        SELECT HOUR(reproducido_en) as hora, COUNT(*) as c
        FROM escuchas
        GROUP BY hora
        ORDER BY hora ASC;
    """)
    hourly_rows = cursor.fetchall()
    hourly_dict = {int(r["hora"]): int(r["c"]) for r in hourly_rows}
    hourly_distribution = [hourly_dict.get(h, 0) for h in range(24)]

    # 7. Día Récord y Días Activos
    cursor.execute("""
        SELECT DATE(reproducido_en) as fecha, COUNT(*) as c
        FROM escuchas
        GROUP BY fecha
        ORDER BY c DESC
        LIMIT 1;
    """)
    row_record_day = cursor.fetchone() or {"fecha": None, "c": 0}
    record_day_count = int(row_record_day.get("c", 0))
    record_day_date = row_record_day.get("fecha")
    meses_es = {
        "January": "Enero", "February": "Febrero", "March": "Marzo", "April": "Abril",
        "May": "Mayo", "June": "Junio", "July": "Julio", "August": "Agosto",
        "September": "Septiembre", "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
    }
    if record_day_date:
        mes_nombre = meses_es.get(record_day_date.strftime("%B"), record_day_date.strftime("%B"))
        record_day_str = f"{record_day_date.day} de {mes_nombre} de {record_day_date.year}"
    else:
        record_day_str = "Día Récord"

    cursor.execute("SELECT COUNT(DISTINCT DATE(reproducido_en)) as dias_activos FROM escuchas;")
    res_dias = cursor.fetchone() or {"dias_activos": 1}
    dias_activos = int(res_dias.get("dias_activos") or 1)
    media_diaria = round(total_escuchas / max(dias_activos, 1), 1)

    # 8. Franjas Horarias (Mañana, Tarde, Noche, Madrugada)
    cursor.execute("""
        SELECT 
            CASE 
                WHEN HOUR(reproducido_en) BETWEEN 6 AND 11 THEN 'Mañana'
                WHEN HOUR(reproducido_en) BETWEEN 12 AND 17 THEN 'Tarde'
                WHEN HOUR(reproducido_en) BETWEEN 18 AND 23 THEN 'Noche'
                ELSE 'Madrugada'
            END as franja,
            COUNT(*) as cnt
        FROM escuchas
        GROUP BY franja
        ORDER BY cnt DESC;
    """)
    franjas_rows = cursor.fetchall()
    franjas_dict = {"Mañana": 0, "Tarde": 0, "Noche": 0, "Madrugada": 0}
    for fr in franjas_rows:
        franjas_dict[fr["franja"]] = int(fr["cnt"])
    top_franja_nombre = franjas_rows[0]["franja"] if franjas_rows else "Tarde"
    top_franja_count = franjas_dict.get(top_franja_nombre, 0)
    top_franja_pct = round((top_franja_count / max(total_escuchas, 1)) * 100)

    # 9. Variedad y Descubrimiento
    variedad_pct = round((canciones_unicas / max(total_escuchas, 1)) * 100)
    
    cursor.close()
    conn.close()
    
    # Determinar arquetipo
    top_song_reps = top_song.get("reproducciones", 0)
    if total_escuchas > 0 and (top_song_reps / total_escuchas) > 0.02:
        archetype = {
            "title": "Adicto al Bucle",
            "emoji": "🔁",
            "subtitle": "Cuando una canción te atrapa, no hay escapatoria",
            "desc": f"Explotas tus temas favoritos hasta la saciedad. ¡Tu tema estrella sonó nada menos que {top_song_reps} veces!",
            "gradient": "linear-gradient(135deg, #10b981 0%, #064e3b 100%)",
            "badge_color": "#10b981"
        }
    elif peak_hour >= 23 or peak_hour <= 5:
        archetype = {
            "title": "Noctámbulo Sónico",
            "emoji": "🌙",
            "subtitle": "La noche es tu hábitat natural",
            "desc": f"Tus mayores sesiones de escucha suceden a altas horas. Tu hora pico fueron las {peak_hour}:00 h.",
            "gradient": "linear-gradient(135deg, #8b5cf6 0%, #31104b 100%)",
            "badge_color": "#8b5cf6"
        }
    elif artistas_unicos > 300:
        archetype = {
            "title": "Explorador Musical",
            "emoji": "🧭",
            "subtitle": "Un apetito insaciable por nuevos sonidos",
            "desc": f"Has navegado por {artistas_unicos} artistas diferentes. Tu gusto musical desafía cualquier algoritmo.",
            "gradient": "linear-gradient(135deg, #06b6d4 0%, #083344 100%)",
            "badge_color": "#06b6d4"
        }
    else:
        archetype = {
            "title": "Melómano Puro",
            "emoji": "🎧",
            "subtitle": "La música es tu banda sonora vital",
            "desc": f"Disfrutas con constancia y fidelidad absoluta. {total_horas} horas acumuladas de pura inmersión auditiva.",
            "gradient": "linear-gradient(135deg, #f59e0b 0%, #78350f 100%)",
            "badge_color": "#f59e0b"
        }
        
    return {
        "volume": {
            "total_escuchas": total_escuchas,
            "canciones_unicas": canciones_unicas,
            "artistas_unicos": artistas_unicos,
            "total_minutos": total_minutos,
            "total_horas": total_horas,
            "dias_continuos": dias_continuos
        },
        "top_song": top_song,
        "top_album": top_album,
        "top_artists": top_artists,
        "top_songs": top_songs,
        "habits": {
            "weekday_count": weekday_count,
            "weekend_count": weekend_count,
            "weekday_pct": weekday_pct,
            "weekend_pct": weekend_pct
        },
        "activity": {
            "peak_hour": peak_hour,
            "peak_day": peak_day,
            "hourly_distribution": hourly_distribution
        },
        "records": {
            "record_day_date": record_day_str,
            "record_day_count": record_day_count,
            "dias_activos": dias_activos,
            "media_diaria": media_diaria
        },
        "time_slots": {
            "slots": franjas_dict,
            "top_slot": top_franja_nombre,
            "top_slot_pct": top_franja_pct
        },
        "diversity": {
            "variedad_pct": variedad_pct,
            "canciones_unicas": canciones_unicas,
            "artistas_unicos": artistas_unicos
        },
        "archetype": archetype
    }
