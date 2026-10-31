# 📻 NaviRadio & Stats Suite

Plataforma integral y automatizada que conecta la **radio en directo** con tu servidor personal de **Navidrome**, tu gestor de descargas **Lidarr**, tu cliente **qBittorrent** y tu base de datos de estadísticas musicales con un **Music Wrapped** interactivo estilo historias 9:16.

---

## 🌟 Características Principales

### 1. 📡 Monitor de Radio y Descubrimientos en Vivo
- **Escucha continua y paralela**: Monitoriza las APIs en tiempo real de las principales emisoras (LOS40, CADENA 100, Dial, KISS FM, etc.).
- **Fuzzy Matching inteligente**: Cruza cada tema detectado con tu catálogo de Navidrome tolerando variaciones sintácticas en artistas y títulos (ej. *Avicii feat. Dan* vs *Avicii, Dan*).
- **Pre-escucha y Reproductor Sticky Flotante**:
  - Eliminación de barras nativas pesadas en cada fila. Ahora la interfaz cuenta con un **Reproductor Flotante Inferior Fijo (Sticky Bottom Player)** estilo Spotify/Apple Music con línea temporal interactiva (30s), volumen y botones de acción rápida.
- **Atajos de Teclado Globales ("Tinder Musical")**:
  - Permite clasificar cientos de canciones a la máxima velocidad sin usar el ratón:
  - **`Flecha Derecha (→)`**: Aceptar canción actual.
  - **`Flecha Izquierda (←)`**: Rechazar canción actual.
  - **`Barra Espaciadora`**: Reproducir / Pausar muestra de 30 segundos.
  - **`Flechas Arriba / Abajo (↑ / ↓)`**: Navegar y enfocar canciones de la lista con auto-scroll suave.
- **Detector de Versiones, Remixes y Edits Radiofónicos ("¡Solo Originales!")**:
  - Detecta automáticamente si una canción es un `Remix`, `Radio Edit`, `Club Mix`, `Versión Acústica`, `En Vivo/Live`, `Cover` o `Sped Up`.
  - **Cruce en tiempo real con Navidrome**: Si la radio emite un remix de un tema cuyo original ya tienes, te avisa con la insignia `✅ Ya tienes el original ("...")`.
  - **Botón `⭐ Pedir Original`**: Permite aceptar la canción convirtiéndola instantáneamente a su título de estudio original limpio para que Lidarr descargue la pista pura sin remixes.
  - **Filtro de Tipo**: Selector en la barra de herramientas para alternar entre `⭐ Todas`, `💿 Solo Originales` y `⚡ Solo Versiones / Remixes`.
- **Modo Rápido Compacto**: Switch tipo iOS integrado en la barra de herramientas que auto-reproduce el siguiente tema de forma fluida conforme aceptas o descartas el actual.
- **Nueva Paleta Visual Minimalista (Obsidian & Slate con Índigo Eléctrico)**:
  - Fondo carbón pizarra profundo sin estridencias, eliminando neones saturados.
  - Filas estilizadas de 48px que permiten visualizar más del doble de canciones por pantalla.
- **Filtros Avanzados en Tiempo Real**:
  - **Ordenación Agrupada por Artista**: En la lista de pendientes, las canciones se muestran ordenadas por volumen de temas por artista (de mayor a menor) manteniendo el diseño limpio y uniforme original de cada tarjeta, apareciendo consecutivas todas las canciones del mismo artista.
  - **Filtro por Emisora**: Selector con el recuento exacto de canciones disponibles por radio.
  - **Filtro por Artista con Desplegable y Buscador Interno**: Menú desplegable con input `🔍` de búsqueda en vivo que filtra los artistas instantáneamente al escribir, con badges de conteo y botón para limpiar filtros.
- **Pestaña 🚫 Rechazadas**:
  - Registro de todas las canciones descartadas con fecha y hora de último cambio (`updated_at`).
  - Ordenadas cronológicamente de forma inversa (las más recientemente rechazadas primero).
  - Botón **`↩ Devolver a Pendiente`** inmediato mediante AJAX sin perder la posición ni recargar la página.
  - Opción de borrado definitivo.

### 2. 🛸 Gestión Automatizada de Descargas (Lidarr + qBittorrent)
- **Petición individual o masiva**:
  - Pide cualquier canción directamente a Lidarr con un clic.
  - Botón **`🛸 Pedir a Lidarr Todos`**: Proceso por lotes en segundo plano con barra de progreso reactiva en tiempo real y porcentaje en pantalla.
- **Rutina de mantenimiento para qBittorrent**:
  - **Automático cada 24 horas**: Hilo demonio que ejecuta *Forzar inicio* (`setForceStart`) para omitir límites de cola en descargas pendientes y *Forzar recomunicación* (`reannounce`) con todos los trackers.
  - **Manual con 1 clic**: Botón **`⚡ Forzar qBittorrent`** en la interfaz para desatascar descargas al instante.

### 3. 📑 Auditoría de Biblioteca y Playlists
- **🪄 Smart Playlists Dinámicas en Navidrome**:
  - **`📻 Descubrimientos de Radio`**: Sincroniza automáticamente en Navidrome las 50 canciones más recientes descubiertas de la radio e incorporadas a tu catálogo.
  - **`🔥 Top 50 Más Escuchados`**: Sincroniza automáticamente en Navidrome tu ranking de canciones más reproducidas extraídas de tus estadísticas.
  - Botón **`🪄 Smart Playlists`** en la interfaz y sincronización automática periódica en segundo plano.
- **👯 Duplicados en Playlist**:
  - Detección en tiempo real de canciones que aparecen múltiples veces en tu playlist de Navidrome (por título, artista o ID de archivo).
  - Indicador de número total de copias en la playlist y álbumes de los que proceden.
  - Reproductor con pre-escucha de 30 segundos.
  - Botón individual **`🧹 Dejar solo 1 copia`** para limpiar cualquier canción concreta.
  - Botón masivo **`🧹 Eliminar Todos los Duplicados a la Vez`**: Limpia todas las copias redundantes de la playlist en lotes descendentes conservando la primera instancia sin alterar el orden del resto.
  - Protección automática contra duplicados: el sistema verifica si la canción ya existe antes de añadirla para prevenir futuras duplicaciones.
- **🎶 Falta Playlist**: Detecta canciones presentes en tu disco/Navidrome que no han sido añadidas aún a tu playlist objetivo y permite vincularlas con un clic.
- **⚠️ Huérfanas y Rotas**:
  - Identifica canciones desaparecidas del disco o renombradas.
  - **Auto-reparación** de enlaces rotos en Navidrome y playlists cuando un archivo ha sido renombrado.
  - Botón para buscar versiones alternativas en Lidarr o desvincular canciones huérfanas de las playlists.

### 4. 📊 Panel de Estadísticas e Historial de Escuchas
- Conexión con base de datos de scrobbles (`spotify_db`).
- **Filtro por periodos temporales**: *Hoy, Semana, Mes, Año o Todo*.
- **Comparativa Temporal de Tendencias**: Tarjeta inteligente que compara el periodo seleccionado contra su anterior equivalente (ej. esta semana vs semana anterior) mostrando variación porcentual de escuchas, temas únicos y el **Artista en Alza** con mayor crecimiento.
- Métricas clave: Minutos totales de escucha, canciones únicas, promedio diario y pico de actividad.
- **Top Canciones Más Escuchadas**: Fila horizontal con portadas circulares idéntica a los artistas más escuchados, con badge dinámico de reproducciones y artista.
- **Top Artistas Más Escuchados**: Círculos interactivos con foto del artista y total de escuchas.
- **Top Álbumes Más Escuchados**: Portadas de álbumes con contador y artista principal.
- Gráficos interactivos con Chart.js (distribución de cuota de escuchas por artista).
- **Historial lineal de reproducciones**: Línea temporal con portada, título, artista, álbum y hora exacta.

### 5. ✨ Music Wrapped Interactivo (Estilo Spotify Wrapped / Historias 9:16)
- **Experiencia vertical 9:16 a pantalla completa**:
  - Barra de progreso segmentada superior con auto-avance programable (5s).
  - Navegación táctil y por clic (35% izquierda = anterior, 65% derecha = siguiente).
  - *Long-press / mantener pulsado* para pausar animaciones y lectura.
- **Diseño visual inmersivo**:
  - Fondos dinámicos continuos con gradientes fluidos CSS (`aurora`, `lava lamp`, etc.).
  - Vinilo giratorio animado con portada y reflejos luminosos.
  - Ecualizador y pulsos reactivos.
  - Contadores numéricos incrementales con easing.
- **9 Historias personalizadas**:
  1. *Volumen Sónico*: Minutos y horas totales escuchadas.
  2. *Tu Tema en Bucle*: Tu obsesión repetitiva con vinilo interactivo.
  3. *El Podio*: Ranking de tus 5 temas más reproducidos.
  4. *Reyes de tus Auriculares*: Tus 5 artistas estrella.
  5. *Álbum del Año*: Tu disco más escuchado.
  6. *Ritmo Biológico*: Tu hora pico y cronometría musical.
  7. *Día Récord*: La jornada con más escuchas del año.
  8. *Brújula Sónica*: Tu momento sagrado (Madrugada, Mañana, Tarde, Noche).
  9. *Arquetipo y Resumen*: Asignación de insignia y perfil melómano (ej. *Adicto al Bucle*, *Noctámbulo Sónico*, *Explorador Musical*, *Melómano Puro*).
- **Randomizador en cada consulta**: Cada vez que abres el Wrapped o pulsas *Repetir*, se eligen colores, gradientes, titulares y citas aleatorias.
- **Exportación Multimedia**:
  - **Descarga individual en PNG** de cada diapositiva.
  - **Descarga en ZIP** con todas las historias en alta resolución.
  - **Exportar GIF Animado**: Grabación y compilación en el cliente con `html2canvas` y `gifshot` optimizada para compartir en redes sociales.

### 6. 📡 Estudio de Rotación de Radio & ¿Manipulación?
- **Auditoría continua de emisiones en tiempo real**: Registra cada evento musical transmitido por las emisoras en una tabla dedicada de alta eficiencia (`radio_emisiones`).
- **Prevención de saturación y almacenamiento ligero**: Gracias a la clave única `(station, artist, title, start_time)` y sentencias `INSERT IGNORE`, almacena todo un año de emisiones (~650.000 registros) en apenas 35 MB sin duplicados ni sobrecarga.
- **Métricas e Índice de Bucle**:
  - Total de canciones emitidas vs canciones únicas reales en emisión.
  - **Índice de Repetición / Bucle (%)**: Mide con precisión qué porcentaje de la parrilla musical son temas repetidos.
- **Ranking de Canciones Más Repetidas ("Las Más Quemadas")**:
  - Cuenta el número exacto de veces que ha sonado cada canción.
  - **Frecuencia media calculada**: Muestra el intervalo promedio entre emisiones (ej. *cada 2h 45m*).
  - Fecha y hora exacta de la última emisión detectada.
- **Comparativa por Emisora**: Ranking de qué radio tiene el mayor porcentaje de bucle y cuál ofrece mayor variedad musical.
- **Top Artistas en Radio**: Listado de los artistas que acumulan más horas y emisiones en las ondas.
- **Filtros Temporales y por Dial**: Permite alternar instantáneamente entre *Hoy, Semana, Mes o Todo el histórico*, así como aislar una emisora concreta.

### 7. 🕒 Zona Horaria de España (`Europe/Madrid`)
- Todas las conexiones SQL establecen automáticamente `SET time_zone = 'Europe/Madrid'`.
- Evita desfases de ±1 hora por el cambio de horario de verano/invierno (Daylight Saving Time).

### 8. 🤖 Bot de Notificaciones en Telegram
- Envío automático de notificaciones a grupos y temas/hilos específicos de Telegram.
- **Canal y Tema configurados**: `https://t.me/c/3998145275/24788` (`chat_id = -1003998145275`, `message_thread_id = 24788`).
- **Avisos automáticos**:
  - Peticiones enviadas a Lidarr (`🛸`).
  - Canciones descargadas con éxito e incorporadas a la playlist de Navidrome (`🎉`).
- Endpoint de prueba: `POST /api/telegram/test`.

---

## 🏗 Arquitectura del Proyecto

```text
Radio2Navidrome/
├── app.py                      # Punto de entrada principal (Flask + hilos en segundo plano)
├── config.py                   # Carga de configuración y variables de entorno
├── database.py                 # Conexiones MariaDB/MySQL con timezone Madrid y migraciones automáticas
├── requirements.txt            # Dependencias de Python
├── docker-compose.yml          # Despliegue con Docker
├── Dockerfile                  # Contenedor Docker
├── routes/
│   ├── __init__.py             # Registro de Blueprints
│   ├── radio_routes.py         # Endpoints de radio, filtrado, descargas y qBittorrent
│   └── stats_routes.py         # Endpoints de estadísticas, historial, rotación de radio y Music Wrapped
├── services/
│   ├── __init__.py
│   ├── radio_monitor.py        # Bucle de escucha continua de emisoras y registro de emisiones
│   ├── radio_stats_service.py  # Análisis de rotación de radio, frecuencias y cálculo de bucle
│   ├── version_detector.py     # Detector inteligente de versiones/remixes y extracción de originales
│   ├── navidrome.py            # Cliente API Subsonic/Navidrome (búsquedas, playlists, estrellas)
│   ├── smart_playlists.py      # Gestor dinámico de Smart Playlists en Navidrome
│   ├── telegram_service.py     # Cliente bot de Telegram con soporte para temas/hilos
│   ├── lidarr.py               # Integración con API de Lidarr (búsqueda y descarga en lote)
│   ├── qbit_service.py         # Integración Web API qBittorrent v2 (forzar inicio y recomunicación)
│   ├── auditor.py              # Auditoría de biblioteca, detección de huérfanas y renombradas
│   ├── stats_service.py        # Consultas analíticas y generación de datos de Wrapped
│   └── utils.py                # Previews de iTunes y utilidades auxiliares
├── static/
│   └── js/
│       ├── html2canvas.min.js  # Captura de elementos DOM para exportación
│       └── gifshot.min.js      # Generación de GIFs en el cliente
└── templates/
    └── index.html              # Interfaz web unificada en modo oscuro con Music Wrapped
```

---

## ⚙️ Configuración (`.env`)

Crea un archivo `.env` en la raíz del proyecto tomando como base `.env.example`:

```env
# ================= NAVIDROME =================
NAVIDROME_URL=https://tu-navidrome.ejemplo.com
NAVIDROME_USER=tu_usuario
NAVIDROME_PASS=tu_contraseña
TARGET_PLAYLIST_NAME=Canciones que te gustan

# ================= LIDARR =================
LIDARR_URL=http://192.168.1.100:8686
LIDARR_API=tu_api_key_de_lidarr

# ================= QBITTORRENT =================
QBIT_URL=http://192.168.1.100:8080
QBIT_USER=admin
QBIT_PASS=tu_contraseña_qbit

# ================= BASE DE DATOS RADIO & LIBRERÍA =================
MYSQL_HOST=192.168.1.100
MYSQL_USER=tu_usuario_db
MYSQL_PASS=tu_contraseña_db
MYSQL_DB=radio_music

# ================= BASE DE DATOS STATS & HISTORIAL =================
STATS_DB_HOST=192.168.1.100
STATS_DB_USER=tu_usuario_stats
STATS_DB_PASS=tu_contraseña_stats
STATS_DB_NAME=spotify_db

# ================= SERVIDOR WEB =================
FLASK_HOST=0.0.0.0
FLASK_PORT=5000

# ================= UMBRALES =================
FUZZY_THRESHOLD=80
```

---

## 🚀 Despliegue e Instalación

### Opción A: Despliegue con Docker (Recomendado)

```bash
docker-compose up -d --build
```

El servicio creará y actualizará automáticamente las tablas necesarias de la base de datos en su primer inicio. Accede desde tu navegador en:
`http://localhost:5000` (o `http://IP_DEL_SERVIDOR:5000`).

### Opción B: Instalación Manual

1. Asegúrate de tener instalado **Python 3.11+**.
2. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Configura tu archivo `.env`.
4. Inicia la aplicación:
   ```bash
   python app.py
   ```

---

## 🔌 Endpoints Principales de la API

| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| `GET` | `/?tab=pendientes` | Vista de canciones pendientes (soporta filtros `&radio=` y `&artist=`) |
| `GET` | `/?tab=rechazadas` | Vista de canciones rechazadas ordenadas por `updated_at DESC` |
| `GET` | `/?tab=descargar` | Vista de canciones aceptadas pendientes de descarga con Lidarr |
| `GET` | `/?tab=playlist` | Canciones descargadas que faltan por añadir a la playlist |
| `GET` | `/?tab=rotas` | Canciones renombradas o desaparecidas del disco |
| `GET` | `/change_status/<id>/<status>` | Cambia el estado a `aceptada`, `rechazada` o `pendiente` |
| `GET` | `/accept_original/<id>` | Limpia el título a la versión original de estudio y la marca como aceptada |
| `POST` | `/send_all_lidarr` | Inicia la petición por lotes a Lidarr en segundo plano |
| `GET` | `/send_all_lidarr_status` | Devuelve el progreso actual del lote de Lidarr |
| `POST` | `/api/qbit/force-refresh` | Fuerza inicio y recomunicación de rastreadores en qBittorrent |
| `GET` | `/api/radio/rotation-stats` | Devuelve rotación de radio, porcentaje de bucle y temas más repetidos |
| `POST` | `/api/smart-playlists/sync` | Sincroniza las playlists inteligentes de Navidrome manualmente |
| `POST` | `/api/telegram/test` | Envía mensaje de prueba al hilo configurado del bot de Telegram |
| `GET` | `/api/stats?period=<periodo>` | Devuelve métricas y datos para los gráficos de estadísticas |
| `GET` | `/api/history?page=<p>` | Devuelve el historial cronológico de reproducciones paginado |
| `GET` | `/api/wrapped` | Devuelve el conjunto completo de datos para el Music Wrapped interactivo |

---

## 🛡️ Notas de Seguridad y Rendimiento
- El archivo `.env` se encuentra ignorado por git (`.gitignore`).
- Las respuestas HTTP incluyen directivas `Cache-Control: no-store, no-cache` para evitar que los navegadores sirvan HTML o scripts desactualizados.
- Las consultas SQL de actualización establecen marcas de tiempo explícitas y `ON UPDATE CURRENT_TIMESTAMP` para una trazabilidad precisa.
