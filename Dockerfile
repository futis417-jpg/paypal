# 1. Imagen base ligera
FROM python:3.9-slim

# 2. Instalación de dependencias del sistema para Chromium
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
    libxrandr2 \
    libgbm1 \
    libasound2 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# 3. Directorio de trabajo
WORKDIR /app
COPY . .

# 4. Instalamos librerías
RUN pip install --no-cache-dir -r requirements.txt

# 5. Instalamos el motor de Playwright
RUN playwright install chromium
RUN playwright install-deps chromium

# 6. Exponemos el puerto para Render
ENV PORT=10000

# 7. Ejecutar con gunicorn para la web y el bot
CMD ["python", "bot.py"]
