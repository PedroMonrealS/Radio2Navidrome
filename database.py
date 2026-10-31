import mysql.connector
from config import (
    MYSQL_HOST, MYSQL_USER, MYSQL_PASS, MYSQL_DB,
    STATS_DB_HOST, STATS_DB_USER, STATS_DB_PASS, STATS_DB_NAME
)

def get_db_connection():
    """Conexión a la base de datos de Radio y Descargas (bibliotecaMusical) con zona horaria de España"""
    return mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASS,
        database=MYSQL_DB,
        init_command="SET time_zone = 'Europe/Madrid'"
    )

def get_stats_db_connection():
    """Conexión a la base de datos de Estadísticas e Historial de Escuchas (spotify_db) con zona horaria de España"""
    return mysql.connector.connect(
        host=STATS_DB_HOST,
        user=STATS_DB_USER,
        password=STATS_DB_PASS,
        database=STATS_DB_NAME,
        init_command="SET time_zone = 'Europe/Madrid'"
    )

def init_db():
    """Inicializa y aplica migraciones a la base de datos de radio si no existen"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Crear tablas base
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS canciones_libreria (
                id INT AUTO_INCREMENT PRIMARY KEY,
                artist VARCHAR(255), title VARCHAR(255),
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_song (artist, title)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS canciones_descubiertas (
                id INT AUTO_INCREMENT PRIMARY KEY,
                artist VARCHAR(255), title VARCHAR(255), station VARCHAR(255),
                estado ENUM('pendiente', 'aceptada', 'rechazada') DEFAULT 'pendiente',
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_song (artist, title)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS radio_emisiones (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                station VARCHAR(100) NOT NULL,
                artist VARCHAR(255) NOT NULL,
                title VARCHAR(255) NOT NULL,
                start_time VARCHAR(50) DEFAULT NULL,
                emitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_emission (station, artist, title, start_time),
                INDEX idx_station_emitted (station, emitted_at),
                INDEX idx_artist_title (artist, title),
                INDEX idx_emitted (emitted_at)
            )
        """)
        
        # Migraciones dinámicas seguras
        columns_libreria = [
            ("navidrome_id", "VARCHAR(255)"),
            ("en_playlist", "BOOLEAN DEFAULT FALSE"),
            ("preview_url", "TEXT"),
            ("ignorar_playlist", "BOOLEAN DEFAULT FALSE"),
            ("estado_archivo", "VARCHAR(50) DEFAULT 'ok'"),
            ("nuevo_navidrome_id", "VARCHAR(255) DEFAULT NULL"),
            ("nuevo_titulo", "VARCHAR(255) DEFAULT NULL"),
            ("nuevo_artista", "VARCHAR(255) DEFAULT NULL"),
            ("last_checked", "TIMESTAMP NULL DEFAULT NULL")
        ]
        for col_name, col_def in columns_libreria:
            try:
                cursor.execute(f"ALTER TABLE canciones_libreria ADD COLUMN {col_name} {col_def}")
            except Exception:
                pass

        columns_descubiertas = [
            ("preview_url", "TEXT"),
            ("lidarr_status", "VARCHAR(50) DEFAULT ''"),
            ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
        ]
        for col_name, col_def in columns_descubiertas:
            try:
                cursor.execute(f"ALTER TABLE canciones_descubiertas ADD COLUMN {col_name} {col_def}")
            except Exception:
                pass
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✓ [Base de Datos] Estructura inicializada correctamente.")
    except Exception as e:
        print(f"✗ [Base de Datos] Error inicializando BD: {e}")
