FROM python:3.10-slim

# Installer Chromium, Node.js 20 LTS et dépendances
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y \
    chromium \
    nodejs \
    fonts-liberation \
    libnss3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dépendances Node.js (@solana/web3.js, ws)
COPY package*.json ./
RUN npm install --production

# Dépendances Python (telethon)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source
COPY . .

# Variables d'environnement pour Render
ENV CHROME_BIN=/usr/bin/chromium
ENV PORT=10000
ENV PYTHONUNBUFFERED=1

EXPOSE 10000

CMD ["python", "cyberleek_telegram_monitor.py"]
