# 1. Usamos una imagen de Python oficial
FROM python:3.9-slim

# 2. Instalamos dependencias del sistema (Corregidas para evitar errores)
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
    && rm -rf /var/lib/apt/lists/*

# 3. Directorio de trabajo
WORKDIR /app
COPY . .

# 4. Instalamos librerías de Python
RUN pip install --no-cache-dir -r requirements.txt

# 5. Instalamos el navegador y sus dependencias internas
RUN playwright install chromium
RUN playwright install-deps chromium

# 6. Ejecutar el bot
CMD ["python", "bot.py"]
