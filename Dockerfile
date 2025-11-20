# Dockerfile

# Usa una imagen base con Python
FROM python:3.10-slim

# Establece el directorio de trabajo
WORKDIR /app

# Instala Chromium y sus dependencias
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    libnss3-dev \
    libgconf-2-4 \
    --no-install-recommends

# CRÍTICO: Asegura permisos de ejecución para los binarios
RUN chmod +x /usr/bin/chromedriver
RUN chmod +x /usr/bin/chromium

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
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
