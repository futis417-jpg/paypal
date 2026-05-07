# Imagen base estable
FROM python:3.9-slim

# Instalamos TODAS las dependencias de fuentes para que el recibo no salga con cuadros
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

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt
# Forzamos la instalación de Chromium para Playwright
RUN playwright install chromium
RUN playwright install-deps chromium

ENV PORT=10000

CMD ["python", "bot.py"]
