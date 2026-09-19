FROM python:3.11-slim

# Instalar dependencias del sistema necesarias (por ejemplo, para compilar python-Levenshtein)
RUN apt-get update && apt-get install -y gcc g++ && rm -rf /var/lib/apt/lists/*

# Establecer directorio de trabajo
WORKDIR /app

# Copiar el archivo de requerimientos e instalarlos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código (app.py y la carpeta templates)
COPY . .

# Exponer el puerto de Flask
EXPOSE 5000

# Variable de entorno para desactivar el buffering de Python (mejor para ver logs en Docker)
ENV PYTHONUNBUFFERED=1

# Comando para ejecutar la aplicación
CMD ["python", "app.py"]
