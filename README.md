# 🚨 Cyberleek Telegram Autonomous Monitor 24/7

Bot autonome de surveillance en temps réel de Cyberleek sur Telegram, connecté on-chain à Solana et déployable gratuitement 24/7 sur Render.

## 🚀 Fonctionnalités
- ⚡ **Scan On-Chain Solana en temps réel** (toutes les 1.5s via RPC) pour détecter immédiatement tout nouveau leak.
- 📊 **Dashboard Cryptos & Votes en direct** (mise à jour silencieuse in-place des messages sans spammer le canal).
- 🗳️ **Calcul précis des votes on-chain** (@solana/web3.js interroge directement les soldes SPL Token des ATAs d'options).
- 📸 **Capture d'écran authentique Chrome CDP** du site Cyberleek lors de chaque nouveau leak.
- 🌐 **Serveur HTTP HealthCheck intégré** sur le port `10000` (`/`) pour le ping 24/7 par UptimeRobot (évite la mise en veille gratuite de Render).

## 🛠️ Déploiement sur Render (100% Gratuit)
1. Créez un **New Web Service** sur [Render.com](https://render.com).
2. Liez ce dépôt GitHub.
3. Environnement : **Docker**.
4. Instance Type : **Free**.
5. Cliquez sur **Deploy Web Service**.

## ⏱️ Activer le 24/7 avec UptimeRobot
1. Rendez-vous sur [UptimeRobot](https://uptimerobot.com).
2. Ajoutez un nouveau monitor **HTTP(s)**.
3. URL : `https://<votre-service>.onrender.com`.
4. Intervalle : **5 minutes** (ou 10 minutes).
Le bot restera éveillé 24h/24 sans jamais s'arrêter !
