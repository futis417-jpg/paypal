# 1. Usamos una imagen de Python oficial
FROM python:3.9-slim

# 2. Instalamos dependencias del sistema para que el navegador funcione
# Esto es lo que permite que el bot "abra" una ventana interna
RUN apt-get update && apt-get install -y \
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
    librandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# 3. Creamos la carpeta de la app y copiamos tus archivos
WORKDIR /app
COPY . .

# 4. Instalamos las librerías de Python (pyrogram, playwright, etc.)
RUN pip install --no-cache-dir -r requirements.txt

# 5. Instalamos el navegador Chromium dentro del contenedor
RUN playwright install chromium
RUN playwright install-deps chromium

# 6. Comando para arrancar tu bot
CMD ["python", "bot.py"]
