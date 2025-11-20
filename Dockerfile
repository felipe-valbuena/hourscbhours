# Dockerfile

# Usa una imagen base con Python
FROM python:3.10-slim

# Establece el directorio de trabajo
WORKDIR /app

# Instala Chromium y sus dependencias (esto resuelve el error del driver)
# Usamos el modo apt-get de Docker, que Render no puede bloquear
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    libnss3-dev \
    libgconf-2-4 \
    --no-install-recommends

# Configura las variables de entorno para que Selenium encuentre el driver
ENV CHROME_DRIVER_PATH /usr/bin/chromedriver
ENV CHROMIUM_PATH /usr/bin/chromium

# Copia los requisitos e instala las dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código
COPY . .

# Expone el puerto que usará Gunicorn
EXPOSE 8000

# Comando de inicio
# Usa el puerto de Render (generalmente 8000 o $PORT)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
