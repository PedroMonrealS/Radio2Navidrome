import time
from database import get_db_connection

def record_radio_emissions_batch(emissions):
    """Inserta en bloque las canciones detectadas en la radio evitando duplicados"""
    if not emissions:
        return 0

    valid_rows = []
    for e in emissions:
        st = e.get('station', '').strip()
        art = e.get('artist', '').strip()
        tit = e.get('title', '').strip()
        start = e.get('start_time')
        
        if not st or not art or not tit:
            continue
            
        try:
            start_epoch = int(start) if start else int(time.time())
        except (ValueError, TypeError):
            start_epoch = int(time.time())
            
        valid_rows.append((st, art, tit, str(start_epoch), start_epoch))

    if not valid_rows:
        return 0

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            INSERT IGNORE INTO radio_emisiones 
            (station, artist, title, start_time, emitted_at)
            VALUES (%s, %s, %s, %s, FROM_UNIXTIME(%s))
        """
        cursor.executemany(query, valid_rows)
        conn.commit()
        inserted = cursor.rowcount
        cursor.close()
        conn.close()
        return inserted
    except Exception as ex:
        print(f"Error registrando emisiones de radio: {ex}")
        return 0

def format_interval(span_minutes, count):
    """Calcula y formatea el intervalo medio de reemisión"""
    if count <= 1 or span_minutes <= 0:
        return "Espaciada"
    avg = round(span_minutes / (count - 1))
    h = avg // 60
    m = avg % 60
    if h > 0:
        return f"Cada ~{h}h {m}m" if m > 0 else f"Cada ~{h}h"
    return f"Cada ~{m}m"

def get_radio_rotation_stats(period='today', station='todas'):
    """Obtiene el informe completo de rotación, repetición y bucle de la radio"""
    where_parts = []
    params = []
    time_condition = ""
    if period == 'today':
        time_condition = "emitted_at >= CURDATE()"
    elif period and period != 'all':
        interval_map = {
            'week': '7 DAY',
            'month': '30 DAY'
        }
        interval = interval_map.get(period, '7 DAY')
        time_condition = f"emitted_at >= DATE_SUB(NOW(), INTERVAL {interval})"

    if time_condition:
        where_parts.append(time_condition)
    if station and station != 'todas':
        where_parts.append("station = %s")
        params.append(station)

    where_clause = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 1. Totales de emisiones y temas únicos
    cursor.execute(f"""
        SELECT 
            COUNT(*) as total_emisiones,
            COUNT(DISTINCT CONCAT(artist, '::', title)) as canciones_unicas
        FROM radio_emisiones
        {where_clause}
    """, tuple(params))
    res_tot = cursor.fetchone() or {}
    total_emisiones = int(res_tot.get('total_emisiones') or 0)
    canciones_unicas = int(res_tot.get('canciones_unicas') or 0)

    # Índice de repetición / bucle (% de emisiones que son temas ya repetidos)
    if total_emisiones > 0:
        indice_repeticion = round((1 - (canciones_unicas / total_emisiones)) * 100, 1)
    else:
        indice_repeticion = 0.0

    # 2. Ranking de canciones más quemadas / repetidas
    cursor.execute(f"""
        SELECT 
            station,
            artist,
            title,
            COUNT(*) as veces_sonada,
            MIN(emitted_at) as primera_emision,
            MAX(emitted_at) as ultima_emision,
            TIMESTAMPDIFF(MINUTE, MIN(emitted_at), MAX(emitted_at)) as span_minutos
        FROM radio_emisiones
        {where_clause}
        GROUP BY station, artist, title
        HAVING veces_sonada > 1
        ORDER BY veces_sonada DESC, ultima_emision DESC
        LIMIT 25
    """, tuple(params))
    top_repetidas = cursor.fetchall()
    for row in top_repetidas:
        row['frecuencia'] = format_interval(row.get('span_minutos', 0), row.get('veces_sonada', 1))
        # Formato amigable de última emisión
        if row.get('ultima_emision'):
            row['ultima_emision_str'] = row['ultima_emision'].strftime('%H:%M - %d/%m')

    # 3. Top Artistas más emitidos en radio
    cursor.execute(f"""
        SELECT 
            artist,
            COUNT(*) as total_emisiones,
            COUNT(DISTINCT title) as canciones_distintas
        FROM radio_emisiones
        {where_clause}
        GROUP BY artist
        ORDER BY total_emisiones DESC
        LIMIT 10
    """, tuple(params))
    top_artistas = cursor.fetchall()

    # 4. Comparativa por Emisoras (sin filtro de estación específica)
    where_time = f"WHERE {time_condition}" if time_condition else ""
    cursor.execute(f"""
        SELECT 
            station,
            COUNT(*) as total,
            COUNT(DISTINCT CONCAT(artist, '::', title)) as unicas
        FROM radio_emisiones
        {where_time}
        GROUP BY station
        ORDER BY total DESC
    """)
    ranking_emisoras = cursor.fetchall()
    for e in ranking_emisoras:
        tot = e['total']
        u = e['unicas']
        e['repeticion_pct'] = round((1 - (u / tot)) * 100, 1) if tot > 0 else 0.0

    # 5. Emisoras disponibles
    cursor.execute("SELECT DISTINCT station FROM radio_emisiones WHERE station IS NOT NULL ORDER BY station ASC")
    available_stations = [r['station'] for r in cursor.fetchall()]

    cursor.close()
    conn.close()

    return {
        "period": period,
        "selected_station": station,
        "total_emisiones": total_emisiones,
        "canciones_unicas": canciones_unicas,
        "indice_repeticion": indice_repeticion,
        "top_repetidas": top_repetidas,
        "top_artistas": top_artistas,
        "ranking_emisoras": ranking_emisoras,
        "available_stations": available_stations
    }
