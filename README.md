# 📻 Radio2Navidrome Monitor

**Radio2Navidrome** es un asistente automatizado que escucha las radios en tiempo real, captura las canciones que suenan y te permite descargarlas automáticamente a tu servidor de música personal.

Este proyecto une el mundo de la radio en vivo con tu librería de **Navidrome** y tu gestor de descargas **Lidarr**.

## ⚙️ ¿Cómo funciona? (El Flujo)

1. 📡 **Escucha activa:** El sistema se conecta a las APIs de varias emisoras de radio y captura en tiempo real lo que está sonando.
2. 🧠 **Cruce de datos:** Verifica automáticamente contra tu servidor **Navidrome** si ya tienes esa canción en tu librería (usando Inteligencia Artificial para tolerar diferencias de nombres, ej: *Avicii feat. Dan* vs *Avicii, Dan*).
3. 🎧 **Panel Web y Pre-escucha:** Si no tienes la canción, la envía a un panel de control web privado. Allí puedes escuchar un fragmento de 30 segundos (gracias a la API de iTunes) para decidir si la quieres o no.
4. 🚀 **Descarga Automática:** Si haces clic en "Añadir a Lidarr", el sistema se conecta a la API de tu **Lidarr**, busca en qué álbum exacto se encuentra la canción, y manda la orden de descargarlo por Torrent.
5. 🔄 **Auto-Playlist:** Un proceso en segundo plano vigila cuándo termina la descarga. En cuanto la canción aparece en tu Navidrome, le da "Me gusta" automáticamente y la mete en tu lista de reproducción favorita.

## 🐳 Despliegue con Docker (Recomendado)

1. Crea un archivo llamado `.env` en la misma carpeta del proyecto.
2. Rellena el archivo con las credenciales de tus servidores. Necesitarás:
   - Base de datos **MySQL/MariaDB** (`MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASS`, `MYSQL_DB`).
   - Conexión a **Navidrome** (`NAVIDROME_URL`, `NAVIDROME_USER`, `NAVIDROME_PASS`, `TARGET_PLAYLIST_NAME`).
   - Conexión a **Lidarr** (`LIDARR_URL`, `LIDARR_API`).
3. Levanta el contenedor:

```bash
docker-compose up -d --build
```

*(El sistema creará las tablas necesarias en la base de datos automáticamente en su primer inicio).*
Accede a tu panel de control desde el navegador en `http://tu-ip:5000`.

## 🛠 Instalación Manual (Sin Docker)

1. Instala Python 3.11 o superior.
2. Instala las librerías necesarias:
```bash
pip install -r requirements.txt
```
3. Crea y rellena tu archivo `.env`.
4. Ejecuta la aplicación:
```bash
python app.py
```

## 📝 Notas de Privacidad
- El archivo `.env` está ignorado por git (`.gitignore`). No subas nunca tus contraseñas ni tus API Keys a repositorios públicos.
