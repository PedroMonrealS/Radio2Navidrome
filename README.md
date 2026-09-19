# 📻 Radio2Navidrome Monitor

Este proyecto es un monitor automatizado que escucha las APIs de las emisoras de radio (Radioplayer) en tiempo real, compara las canciones con tu librería de [Navidrome](https://www.navidrome.org/), y te permite gestionar su descarga y clasificación.

Cuenta con un panel Web interactivo y una integración avanzada con Navidrome para gestionar tus listas de reproducción automáticamente.

## ✨ Características Principales
- **Escucha 24/7:** Monitorea múltiples emisoras de radio simultáneamente.
- **Fuzzy Matching:** Inteligencia artificial básica para detectar que "Avicii,Dan Tyminski" y "Avicii - Hey Brother (feat. Dan Tyminski)" son la misma canción, incluso si los textos difieren.
- **Panel de Control Web (Flask):** Gestiona tus pendientes, añade canciones a mano y revisa lo que ya tienes.
- **Pre-escucha de 30s:** Se integra con la API gratuita de Apple iTunes para ofrecerte un mini reproductor con el estribillo de la canción descubierta antes de decidir si descargarla.
- **Sincronización con Playlists:** Capacidad para añadir canciones directamente a tu lista de favoritos de Navidrome (dando "Me gusta" de forma automática y guardándola en la playlist).

## 🚀 Despliegue con Docker (Recomendado)

1. Renombra el archivo `.env.example` a `.env`.
2. Rellena el archivo `.env` con tus credenciales reales (Navidrome y MySQL).
3. Asegúrate de tener una base de datos MySQL corriendo y accesible. El script creará las tablas automáticamente en el primer inicio.
4. Levanta el contenedor:

```bash
docker-compose up -d --build
```

El panel de control estará disponible en `http://tu-ip:5000`.

## 🛠 Instalación Manual (Sin Docker)

1. Instala Python 3.11+.
2. Instala las dependencias:
```bash
pip install -r requirements.txt
```
3. Renombra `.env.example` a `.env` y rellénalo.
4. Ejecuta la aplicación:
```bash
python app.py
```

## 🗄 Estructura de la Base de Datos
- `canciones_libreria`: Registro de las canciones que ya tienes en Navidrome.
- `canciones_descubiertas`: Canciones procesadas desde la radio. Pueden estar en estado `pendiente`, `aceptada` o `rechazada`.

## 📝 Notas
- El archivo `.env` está en el `.gitignore` por seguridad para que no subas tus contraseñas accidentalmente a GitHub.
