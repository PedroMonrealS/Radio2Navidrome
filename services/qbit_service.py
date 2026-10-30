# -*- coding: utf-8 -*-
import time
import requests
from config import QBIT_URL, QBIT_USER, QBIT_PASS

def get_qbit_session():
    """Crea una sesión autenticada con qBittorrent Web API"""
    session = requests.Session()
    res = session.post(
        f"{QBIT_URL}/api/v2/auth/login",
        data={"username": QBIT_USER, "password": QBIT_PASS},
        timeout=10
    )
    if res.status_code != 200 and res.status_code != 204:
        raise Exception(f"Fallo de login en qBittorrent: HTTP {res.status_code}")
    return session

def force_start_and_reannounce_torrents(target="unfinished"):
    """
    Fuerza el inicio (bypassing límites de cola) y la recomunicación con todos los trackers.
    target: 'unfinished' (solo descargas no completadas) o 'all' (todos los torrents)
    """
    try:
        session = get_qbit_session()
        torrents = session.get(f"{QBIT_URL}/api/v2/torrents/info", timeout=10).json()
        
        if not torrents:
            print("[qBittorrent] No hay torrents en la lista.", flush=True)
            return {"success": True, "forced_count": 0, "total_torrents": 0}

        if target == "unfinished":
            # Filtrar descargas activas, en cola, estancadas o con progreso < 100%
            target_torrents = [t for t in torrents if t.get('progress', 0) < 1.0 or 'DL' in t.get('state', '')]
        else:
            target_torrents = torrents

        hashes_to_force = [t['hash'] for t in target_torrents]

        if hashes_to_force:
            hash_str = "|".join(hashes_to_force)
            # 1. Iniciar torrents si estaban pausados / parados
            session.post(f"{QBIT_URL}/api/v2/torrents/start", data={"hashes": hash_str}, timeout=10)
            
            # 2. Forzar inicio (ignora límites de cola y pone en marcha inmediatamente)
            session.post(f"{QBIT_URL}/api/v2/torrents/setForceStart", data={"hashes": hash_str, "value": "true"}, timeout=10)

        # 3. Forzar recomunicación con todos los rastreadores para todos los torrents
        session.post(f"{QBIT_URL}/api/v2/torrents/reannounce", data={"hashes": "all"}, timeout=10)

        msg = f"[qBittorrent] Exito: {len(hashes_to_force)} descargas forzadas e iniciadas. Recomunicacion enviada a todos los trackers."
        print(msg, flush=True)
        return {
            "success": True,
            "forced_count": len(hashes_to_force),
            "total_torrents": len(torrents),
            "message": msg
        }
    except Exception as e:
        err = f"[qBittorrent] Error forzando inicio y recomunicacion: {e}"
        print(err, flush=True)
        return {"success": False, "error": str(e), "message": err}

def qbit_maintenance_loop():
    """Bucle en segundo plano que ejecuta el mantenimiento de qBittorrent cada 24 horas"""
    print("[qBittorrent] Tarea diaria de mantenimiento iniciada (Forzar inicio & Recomunicacion cada 24h).", flush=True)
    # Espera inicial de 30 segundos tras arrancar Flask
    time.sleep(30)
    
    while True:
        try:
            print("[qBittorrent] Ejecutando rutina programada de forzar inicio y recomunicacion...", flush=True)
            force_start_and_reannounce_torrents(target="unfinished")
        except Exception as e:
            print(f"[qBittorrent] Error en ciclo de mantenimiento: {e}", flush=True)
        
        # Dormir 24 horas (86400 segundos) hasta la siguiente ejecución
        time.sleep(86400)
