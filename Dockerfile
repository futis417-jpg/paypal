# 1. Usamos una imagen de Python ligera pero compatible
FROM python:3.9-slim

# 2. Instalamos dependencias del sistema y FUENTES
# Esto es lo más importante para que el recibo se vea REAL
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    fonts-liberation \
    fonts-noto-color-emoji \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# 3. Directorio de trabajo
WORKDIR /app

# 4. Copiamos los archivos del repositorio
COPY . .

# 5. Instalamos las librerías de Python
RUN pip install --no-cache-dir -r requirements.txt

# 6. Instalamos Chromium y sus dependencias internas
# Forzamos la instalación para evitar errores en el despliegue
RUN playwright install chromium
RUN playwright install-deps chromium

# 7. Configuramos el puerto (Render usa el 10000 por defecto)
ENV PORT=10000

# 8. Comando para arrancar el bot e Ishak empiece a ganar dinero
CMD ["python", "bot.py"]
