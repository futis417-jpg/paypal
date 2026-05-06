# 1. Imagen base de Python
FROM python:3.9-slim

# 2. Instalación de dependencias del sistema necesarias para Chromium y Playwright
# Añadimos dependencias para que funcione en entornos sin monitor (headless)
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
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
    libpango-1.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# 3. Directorio de trabajo
WORKDIR /app
COPY . .

# 4. Instalamos librerías de Python
RUN pip install --no-cache-dir -r requirements.txt

# 5. Instalamos Chromium y sus dependencias internas de Playwright
RUN playwright install chromium
RUN playwright install-deps chromium

# 6. Puerto para Render (Variable de entorno)
ENV PORT=10000

# 7. Ejecutar el bot
# Usamos python directo porque el bot ya maneja el hilo de Flask
CMD ["python", "bot.py"]
