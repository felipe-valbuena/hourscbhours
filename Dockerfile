# Dockerfile (SOLUCIÓN FINAL CON IMAGEN DE CHROME/SELENIUM)

# Usamos la imagen de Selenium que ya tiene Chrome preinstalado
FROM selenium/standalone-chrome:latest

# Instalar Python 3.10 y PIP (ya que la imagen de Selenium no lo incluye)
# Solo instalamos Python, evitando el apt-get de Chrome que fallaba.
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    python3.10-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Establecer el directorio de trabajo
WORKDIR /app

# Configurar Python 3.10 como intérprete predeterminado
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1
RUN update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

# Copia los requisitos e instala las dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código
COPY . .

# Rutas de Chrome configuradas por la imagen de Selenium
ENV CHROMIUM_PATH /usr/bin/google-chrome
ENV CHROME_DRIVER_PATH /usr/bin/chromedriver

# Comando de inicio
EXPOSE 8000
CMD ["python", "-m", "gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
