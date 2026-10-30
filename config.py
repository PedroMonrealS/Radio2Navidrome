import os
from dotenv import load_dotenv

load_dotenv()

# ================= RADIOS =================
RADIO_API_URLS = [
    "https://core-search.radioplayer.cloud/724/qp/v4/events?rpId=404",
    "https://core-search.radioplayer.cloud/724/qp/v4/events?rpId=301",
    "https://core-search.radioplayer.cloud/724/qp/v4/events?rpId=405",
    "https://core-search.radioplayer.cloud/724/qp/v4/events?rpId=402",
    "https://core-search.radioplayer.cloud/724/qp/v4/events?rpId=167"
]

# ================= NAVIDROME =================
NAVIDROME_URL = os.environ.get("NAVIDROME_URL", "")
NAVIDROME_USER = os.environ.get("NAVIDROME_USER", "")
NAVIDROME_PASS = os.environ.get("NAVIDROME_PASS", "")
TARGET_PLAYLIST_NAME = os.environ.get("TARGET_PLAYLIST_NAME", "Canciones que te gustan")

# ================= LIDARR =================
LIDARR_URL = os.environ.get("LIDARR_URL", "")
LIDARR_API = os.environ.get("LIDARR_API", "")

# ================= QBITTORRENT =================
QBIT_URL = os.environ.get("QBIT_URL", "http://192.168.4.147:8080")
QBIT_USER = os.environ.get("QBIT_USER", "admin")
QBIT_PASS = os.environ.get("QBIT_PASS", "287DryMops")

# ================= BASE DE DATOS RADIO & LIBRERIA =================
MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASS = os.environ.get("MYSQL_PASS", "")
MYSQL_DB = os.environ.get("MYSQL_DB", "radio_music")

# ================= BASE DE DATOS STATS & HISTORIAL =================
STATS_DB_HOST = os.environ.get("STATS_DB_HOST", MYSQL_HOST)
STATS_DB_USER = os.environ.get("STATS_DB_USER", "n8n")
STATS_DB_PASS = os.environ.get("STATS_DB_PASS", "gI1_lKF5Pq8K[old")
STATS_DB_NAME = os.environ.get("STATS_DB_NAME", "spotify_db")

# ================= SERVIDOR WEB =================
FLASK_HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.environ.get("FLASK_PORT", 5000))

# ================= UMBRALES =================
FUZZY_THRESHOLD = int(os.environ.get("FUZZY_THRESHOLD", 80))
