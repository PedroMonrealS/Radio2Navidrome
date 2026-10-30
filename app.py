import sys
import threading
from flask import Flask

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from config import FLASK_HOST, FLASK_PORT
from database import init_db
from routes import radio_bp, stats_bp
from services.radio_monitor import radio_monitor_loop
from services.auditor import audit_library
from services.qbit_service import qbit_maintenance_loop

app = Flask(__name__)

# Registrar Blueprints modulares
app.register_blueprint(radio_bp)
app.register_blueprint(stats_bp)

@app.after_request
def add_no_cache_headers(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

if __name__ == '__main__':
    print("🚀 Inicializando base de datos...")
    init_db()
    
    # Iniciar monitor de emisoras de radio en segundo plano
    monitor_thread = threading.Thread(target=radio_monitor_loop, daemon=True)
    monitor_thread.start()
    
    # Iniciar auditoría de biblioteca en segundo plano
    audit_thread = threading.Thread(target=audit_library, daemon=True)
    audit_thread.start()
    
    # Iniciar mantenimiento de qBittorrent en segundo plano (cada 24 horas)
    qbit_thread = threading.Thread(target=qbit_maintenance_loop, daemon=True)
    qbit_thread.start()
    
    # Iniciar servidor web Flask
    print(f"📻 NaviRadio & Stats iniciado en http://{FLASK_HOST}:{FLASK_PORT}")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=False)
