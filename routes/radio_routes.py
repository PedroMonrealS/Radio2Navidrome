from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from database import get_db_connection
from services.utils import get_itunes_preview
from services.navidrome import (
    search_in_navidrome,
    get_target_playlist_id,
    get_playlist_track_ids,
    add_song_to_playlist,
    remove_song_from_playlist,
    star_song_in_navidrome
)
from services.lidarr import request_lidarr_song, get_live_download_status
from services.auditor import (
    audit_library,
    sync_aceptadas_to_libreria,
    sync_playlist_faltantes
)

radio_bp = Blueprint('radio_bp', __name__)

def ajax_response(success=True):
    return jsonify({"success": success})

@radio_bp.route('/')
def index():
    tab = request.args.get('tab', 'pendientes')
    page = int(request.args.get('page', 1))
    per_page = 30
    offset = (page - 1) * per_page
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Obtener totales para los contadores de las pestañas
    cursor.execute("SELECT COUNT(*) as c FROM canciones_descubiertas WHERE estado = 'pendiente'")
    count_pendientes = cursor.fetchone()['c']
    
    cursor.execute("SELECT COUNT(*) as c FROM canciones_descubiertas WHERE estado = 'aceptada'")
    count_aceptadas = cursor.fetchone()['c']
    
    cursor.execute("SELECT COUNT(*) as c FROM canciones_libreria WHERE en_playlist = FALSE AND ignorar_playlist = FALSE")
    count_sin_playlist = cursor.fetchone()['c']
    
    cursor.execute("SELECT COUNT(*) as c FROM canciones_libreria WHERE estado_archivo != 'ok'")
    count_rotas = cursor.fetchone()['c']
    
    cursor.execute("SELECT COUNT(*) as c FROM canciones_libreria WHERE estado_archivo = 'renombrada'")
    count_renombradas = cursor.fetchone()['c']
    
    cursor.execute("SELECT COUNT(*) as c FROM canciones_libreria WHERE estado_archivo = 'desaparecida'")
    count_desaparecidas = cursor.fetchone()['c']
    
    # Obtener los datos de la pestaña actual paginados
    data = []
    total_items = 0
    filtro = request.args.get('filtro', 'todas')
    
    if tab == 'pendientes':
        total_items = count_pendientes
        cursor.execute("SELECT * FROM canciones_descubiertas WHERE estado = 'pendiente' ORDER BY discovered_at DESC LIMIT %s OFFSET %s", (per_page, offset))
        data = cursor.fetchall()
    elif tab == 'descargar':
        total_items = count_aceptadas
        cursor.execute("SELECT * FROM canciones_descubiertas WHERE estado = 'aceptada' ORDER BY discovered_at DESC LIMIT %s OFFSET %s", (per_page, offset))
        data = cursor.fetchall()
    elif tab == 'playlist':
        total_items = count_sin_playlist
        cursor.execute("SELECT * FROM canciones_libreria WHERE en_playlist = FALSE AND ignorar_playlist = FALSE ORDER BY added_at DESC LIMIT %s OFFSET %s", (per_page, offset))
        data = cursor.fetchall()
    elif tab == 'rotas':
        if filtro == 'desaparecidas':
            cursor.execute("SELECT COUNT(*) as c FROM canciones_libreria WHERE estado_archivo = 'desaparecida'")
            total_items = cursor.fetchone()['c']
            cursor.execute("SELECT * FROM canciones_libreria WHERE estado_archivo = 'desaparecida' ORDER BY en_playlist DESC, id DESC LIMIT %s OFFSET %s", (per_page, offset))
        elif filtro == 'renombradas':
            cursor.execute("SELECT COUNT(*) as c FROM canciones_libreria WHERE estado_archivo = 'renombrada'")
            total_items = cursor.fetchone()['c']
            cursor.execute("SELECT * FROM canciones_libreria WHERE estado_archivo = 'renombrada' ORDER BY id DESC LIMIT %s OFFSET %s", (per_page, offset))
        else:
            cursor.execute("SELECT COUNT(*) as c FROM canciones_libreria WHERE estado_archivo != 'ok'")
            total_items = cursor.fetchone()['c']
            cursor.execute("SELECT * FROM canciones_libreria WHERE estado_archivo != 'ok' ORDER BY FIELD(estado_archivo, 'renombrada', 'desaparecida'), en_playlist DESC, id DESC LIMIT %s OFFSET %s", (per_page, offset))
        data = cursor.fetchall()
        
    conn.close()
    
    total_pages = (total_items + per_page - 1) // per_page
    
    return render_template('index.html', 
                           data=data, 
                           tab=tab, 
                           page=page, 
                           total_pages=total_pages,
                           filtro=filtro,
                           counts={
                               'pendientes': count_pendientes, 
                               'descargar': count_aceptadas, 
                               'playlist': count_sin_playlist,
                               'rotas': count_rotas,
                               'renombradas': count_renombradas,
                               'desaparecidas': count_desaparecidas
                           })

@radio_bp.route('/force_sync')
def force_sync():
    sync_aceptadas_to_libreria()
    sync_playlist_faltantes()
    return redirect(url_for('.index', tab=request.args.get('tab', 'descargar')))

@radio_bp.route('/add_manual', methods=['POST'])
def add_manual():
    artist = request.form.get('artist')
    title = request.form.get('title')
    if artist and title:
        preview = get_itunes_preview(title, artist)
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO canciones_descubiertas (artist, title, station, estado, preview_url) VALUES (%s, %s, %s, 'aceptada', %s)",
                (artist, title, 'Manual', preview)
            )
            conn.commit()
            conn.close()
        except:
            pass
    return redirect(url_for('.index', tab='descargar'))

@radio_bp.route('/change_status/<int:song_id>/<status>')
def change_status(song_id, status):
    if status in ['aceptada', 'rechazada', 'pendiente']:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE canciones_descubiertas SET estado = %s WHERE id = %s", (status, song_id))
            conn.commit()
            conn.close()
        except:
            pass
    if request.args.get('ajax'):
        return ajax_response()
    return redirect(url_for('.index', tab=request.args.get('tab', 'pendientes')))

@radio_bp.route('/send_lidarr/<int:song_id>')
def send_lidarr(song_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT title, artist FROM canciones_descubiertas WHERE id = %s", (song_id,))
        row = cursor.fetchone()
        
        if row:
            success, msg = request_lidarr_song(row['artist'], row['title'])
            if success:
                cursor.execute("UPDATE canciones_descubiertas SET lidarr_status = 'enviado' WHERE id = %s", (song_id,))
                conn.commit()
            conn.close()
            if request.args.get('ajax'):
                return jsonify({"success": success, "message": msg})
            return redirect(url_for('.index', tab='descargar'))
    except Exception as e:
        pass
        
    if request.args.get('ajax'):
        return jsonify({"success": False, "message": "Error interno"})
    return redirect(url_for('.index', tab='descargar'))

@radio_bp.route('/live_status/<int:song_id>')
def live_status(song_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT title, artist FROM canciones_descubiertas WHERE id = %s", (song_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return jsonify({"status_text": "Error"})
        
        status_info = get_live_download_status(row['artist'])
        return jsonify(status_info)
    except Exception as e:
        return jsonify({"status_text": "✗ Error conectando a Qbit/Lidarr", "color": "#dc3545"})

@radio_bp.route('/delete/<int:song_id>')
def delete_song(song_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM canciones_descubiertas WHERE id = %s", (song_id,))
        conn.commit()
        conn.close()
    except:
        pass
    if request.args.get('ajax'):
        return ajax_response()
    return redirect(url_for('.index', tab='descargar'))

@radio_bp.route('/ignore_playlist/<int:db_id>')
def ignore_playlist(db_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE canciones_libreria SET ignorar_playlist = TRUE WHERE id = %s", (db_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error omitiendo playlist: {e}")
    if request.args.get('ajax'):
        return ajax_response()
    return redirect(url_for('.index', tab='playlist'))

@radio_bp.route('/add_to_navidrome_playlist/<int:db_id>')
def add_to_navidrome_playlist_route(db_id):
    success = False
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT title, artist, navidrome_id FROM canciones_libreria WHERE id = %s", (db_id,))
        row = cursor.fetchone()
        
        if row:
            nav_id = row['navidrome_id']
            if not nav_id:
                in_nav, nav_id = search_in_navidrome(row['title'], row['artist'])
                if nav_id:
                    cursor.execute("UPDATE canciones_libreria SET navidrome_id = %s WHERE id = %s", (nav_id, db_id))
                    conn.commit()
            
            if nav_id:
                playlist_id = get_target_playlist_id()
                if playlist_id:
                    current_tracks = get_playlist_track_ids(playlist_id)
                    if nav_id in current_tracks:
                        success = True
                    else:
                        success = add_song_to_playlist(playlist_id, nav_id)
                
                star_song_in_navidrome(nav_id)
                
                if success:
                    cursor.execute("UPDATE canciones_libreria SET en_playlist = TRUE WHERE id = %s", (db_id,))
                    conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error añadiendo a playlist/favoritos: {e}")
        
    if request.args.get('ajax'):
        return ajax_response(success)
    return redirect(url_for('.index', tab='playlist'))

@radio_bp.route('/run_audit')
def run_audit():
    audit_library()
    return redirect(url_for('.index', tab='rotas'))

@radio_bp.route('/fix_renamed/<int:db_id>')
def fix_renamed(db_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, title, artist, navidrome_id, nuevo_navidrome_id, nuevo_titulo, nuevo_artista, en_playlist FROM canciones_libreria WHERE id = %s", (db_id,))
        row = cursor.fetchone()
        
        if row and row['nuevo_navidrome_id']:
            new_id = row['nuevo_navidrome_id']
            old_id = row['navidrome_id']
            playlist_id = get_target_playlist_id()
            
            # Si estaba en playlist o debía estar, actualizamos en Navidrome
            if row['en_playlist'] and playlist_id:
                if old_id:
                    remove_song_from_playlist(playlist_id, old_id)
                add_song_to_playlist(playlist_id, new_id)
                star_song_in_navidrome(new_id)
            
            new_title = row['nuevo_titulo'] or row['title']
            new_artist = row['nuevo_artista'] or row['artist']
            
            cursor.execute("""
                UPDATE canciones_libreria 
                SET navidrome_id = %s,
                    title = %s,
                    artist = %s,
                    estado_archivo = 'ok',
                    nuevo_navidrome_id = NULL,
                    nuevo_titulo = NULL,
                    nuevo_artista = NULL
                WHERE id = %s
            """, (new_id, new_title, new_artist, db_id))
            conn.commit()
            
        conn.close()
        if request.args.get('ajax'):
            return ajax_response(True)
    except Exception as e:
        print(f"Error reparando canción renombrada: {e}")
        if request.args.get('ajax'):
            return jsonify({"success": False, "message": str(e)})
    return redirect(url_for('.index', tab='rotas'))

@radio_bp.route('/fix_all_renamed')
def fix_all_renamed():
    count_repaired = 0
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, title, artist, navidrome_id, nuevo_navidrome_id, nuevo_titulo, nuevo_artista, en_playlist FROM canciones_libreria WHERE estado_archivo = 'renombrada'")
        rows = cursor.fetchall()
        playlist_id = get_target_playlist_id()
        
        for row in rows:
            if row['nuevo_navidrome_id']:
                new_id = row['nuevo_navidrome_id']
                old_id = row['navidrome_id']
                if row['en_playlist'] and playlist_id:
                    if old_id:
                        remove_song_from_playlist(playlist_id, old_id)
                    add_song_to_playlist(playlist_id, new_id)
                    star_song_in_navidrome(new_id)
                
                new_title = row['nuevo_titulo'] or row['title']
                new_artist = row['nuevo_artista'] or row['artist']
                cursor.execute("""
                    UPDATE canciones_libreria 
                    SET navidrome_id = %s, title = %s, artist = %s, estado_archivo = 'ok',
                        nuevo_navidrome_id = NULL, nuevo_titulo = NULL, nuevo_artista = NULL
                    WHERE id = %s
                """, (new_id, new_title, new_artist, row['id']))
                count_repaired += 1
                
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error reparando todas: {e}")
    return redirect(url_for('.index', tab='rotas'))

@radio_bp.route('/remove_from_playlist/<int:db_id>')
def remove_from_playlist_route(db_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, navidrome_id, nuevo_navidrome_id FROM canciones_libreria WHERE id = %s", (db_id,))
        row = cursor.fetchone()
        if row:
            playlist_id = get_target_playlist_id()
            if playlist_id:
                if row['navidrome_id']:
                    remove_song_from_playlist(playlist_id, row['navidrome_id'])
                if row['nuevo_navidrome_id']:
                    remove_song_from_playlist(playlist_id, row['nuevo_navidrome_id'])
            
            cursor.execute("UPDATE canciones_libreria SET en_playlist = FALSE WHERE id = %s", (db_id,))
            conn.commit()
        conn.close()
        if request.args.get('ajax'):
            return ajax_response(True)
    except Exception as e:
        print(f"Error quitando de playlist: {e}")
        if request.args.get('ajax'):
            return jsonify({"success": False, "message": str(e)})
    return redirect(url_for('.index', tab='rotas'))

@radio_bp.route('/clean_all_orphans_playlist')
def clean_all_orphans_playlist():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, navidrome_id FROM canciones_libreria WHERE estado_archivo = 'desaparecida' AND en_playlist = TRUE")
        rows = cursor.fetchall()
        playlist_id = get_target_playlist_id()
        for r in rows:
            if playlist_id and r['navidrome_id']:
                remove_song_from_playlist(playlist_id, r['navidrome_id'])
            cursor.execute("UPDATE canciones_libreria SET en_playlist = FALSE WHERE id = %s", (r['id'],))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error limpiando huérfanas de playlist: {e}")
    return redirect(url_for('.index', tab='rotas'))

@radio_bp.route('/delete_libreria/<int:db_id>')
def delete_libreria(db_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, navidrome_id, en_playlist FROM canciones_libreria WHERE id = %s", (db_id,))
        row = cursor.fetchone()
        if row:
            if row['en_playlist'] and row['navidrome_id']:
                playlist_id = get_target_playlist_id()
                if playlist_id:
                    remove_song_from_playlist(playlist_id, row['navidrome_id'])
            cursor.execute("DELETE FROM canciones_libreria WHERE id = %s", (db_id,))
            conn.commit()
        conn.close()
        if request.args.get('ajax'):
            return ajax_response(True)
    except Exception as e:
        print(f"Error borrando de BD: {e}")
        if request.args.get('ajax'):
            return jsonify({"success": False, "message": str(e)})
    return redirect(url_for('.index', tab='rotas'))

@radio_bp.route('/redownload_song/<int:db_id>', methods=['GET', 'POST'])
def redownload_song(db_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, title, artist, navidrome_id, preview_url, en_playlist FROM canciones_libreria WHERE id = %s", (db_id,))
        row = cursor.fetchone()
        
        if row:
            target_artist = request.form.get('artist') or row['artist']
            target_title = request.form.get('title') or row['title']
            
            # Quitar de playlist en Navidrome si estaba
            playlist_id = get_target_playlist_id()
            if playlist_id and row['navidrome_id'] and row['en_playlist']:
                remove_song_from_playlist(playlist_id, row['navidrome_id'])
            
            # Borrar de canciones_libreria
            cursor.execute("DELETE FROM canciones_libreria WHERE id = %s", (db_id,))
            
            # Insertar en canciones_descubiertas como 'aceptada'
            preview = row['preview_url'] or get_itunes_preview(target_title, target_artist)
            cursor.execute("""
                INSERT INTO canciones_descubiertas (artist, title, station, estado, preview_url, lidarr_status)
                VALUES (%s, %s, 'Re-descarga', 'aceptada', %s, 'enviado')
                ON DUPLICATE KEY UPDATE estado = 'aceptada', lidarr_status = 'enviado', preview_url = VALUES(preview_url)
            """, (target_artist, target_title, preview))
            conn.commit()
            conn.close()
            
            # Lanzar petición a Lidarr
            success, msg = request_lidarr_song(target_artist, target_title)
            
            if request.args.get('ajax'):
                return jsonify({"success": True, "message": f"Enviada a Lidarr: {msg}"})
            return redirect(url_for('.index', tab='descargar'))
            
        conn.close()
    except Exception as e:
        print(f"Error re-descargando canción: {e}")
        if request.args.get('ajax'):
            return jsonify({"success": False, "message": str(e)})
    return redirect(url_for('.index', tab='rotas'))
