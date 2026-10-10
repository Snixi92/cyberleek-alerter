"""
====================================================================
CYBERLEEK TELEGRAM AUTONOMOUS MONITOR
Surveillance ultra-rapide et silencieuse de Cyberleek sur Telegram
====================================================================
"""

import sys
import os
import json
import time
import base64
import struct
import datetime
import urllib.request
import urllib.error
import ssl
import subprocess
import asyncio
from telethon import TelegramClient, types
from telethon.errors import MessageNotModifiedError
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"CYBERLEEK MONITOR ONLINE 24/7 OK")
    def log_message(self, format, *args):
        pass

def start_health_server():
    port = int(os.environ.get("PORT", 10000))
    try:
        server = HTTPServer(("0.0.0.0", port), HealthHandler)
        print(f"[HealthCheck] Serveur HTTP actif sur le port {port} (pour Render / UptimeRobot)", flush=True)
        server.serve_forever()
    except Exception as e:
        print(f"[HealthCheck Notice] {e}", flush=True)

# Forcer UTF-8 sur Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Credentials Telegram (supporte variables d'environnement pour Render)
API_ID = int(os.environ.get("TELEGRAM_API_ID", "32755876"))
API_HASH = os.environ.get("TELEGRAM_API_HASH", "d7c46be11bfc28c9825330b26310ceb0")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8985354063:AAHp-c4YNe0YI9Is0IeplCgXmz0c-wYsxDg")
CHANNEL_ID = int(os.environ.get("TELEGRAM_CHANNEL_ID", "-1003932229737"))


# Endpoints & Solana Protocol
RPC_ENDPOINTS = [
    "https://api.mainnet-beta.solana.com",
    "https://public.rpc.solanavibestation.com",
    "https://solana.api.pocket.network"
]
current_rpc_idx = 0

PROGRAM_ID = "7rAgHPLDc9NryZmNdeEzyDui6D9PHkvTxMjKhNSa7w3a"
TOKEN_ADDRESS = "ApZuxdpzMrbEYTGEzeY9afh5pj9d6qPRJCTgQYiipbKg"

DISCRIMINATORS = {
    "leek": "G6JNBZ2BSey",     # Taille 7156
    "poll": "5Qpj1hsHT4k"      # Taille 2800
}

MIRRORS = [
    "https://cyberleek.ar.perma.online/",
    "https://wayfinder.vilenarios.com/?q=cyberleek",
    "https://cyberleek.saiph.weavegate.net/"
]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SEEN_FILE = os.path.join(SCRIPT_DIR, "seen_leaks_tg.json")
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
SCREENSHOT_PATH = os.path.join(SCRIPT_DIR, "live_leak_screenshot.png")

def get_rpc():
    global current_rpc_idx
    return RPC_ENDPOINTS[current_rpc_idx % len(RPC_ENDPOINTS)]

def switch_rpc():
    global current_rpc_idx
    current_rpc_idx = (current_rpc_idx + 1) % len(RPC_ENDPOINTS)

def load_seen():
    if not os.path.exists(SEEN_FILE):
        return {"leeks": [], "initialized": False}
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"leeks": [], "initialized": False}

def save_seen(data):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

class BinaryReader:
    def __init__(self, data):
        self.data = data
        self.offset = 0
    def pos(self): return self.offset
    def seek(self, p): self.offset = p
    def i64(self):
        val = struct.unpack_from("<q", self.data, self.offset)[0]
        self.offset += 8
        return val
    def u32(self):
        val = struct.unpack_from("<I", self.data, self.offset)[0]
        self.offset += 4
        return val
    def bytes(self, length):
        val = self.data[self.offset:self.offset + length]
        self.offset += length
        return val
    def str(self):
        l = self.u32()
        b = self.bytes(l)
        return b.decode('utf-8', errors='replace')
    def vec(self, fn):
        cnt = self.u32()
        return [fn() for _ in range(cnt)]

def decode_leek(raw_bytes):
    try:
        reader = BinaryReader(raw_bytes[8:])
        authority = reader.bytes(32)
        timestamp = reader.i64()
        title = reader.str()
        saved_pos = reader.pos()
        try:
            items = reader.vec(lambda: {"label": reader.str(), "url": reader.str()})
        except Exception:
            reader.seek(saved_pos)
            s = reader.str()
            items = [{"label": s, "url": s}]
        return {
            "timestamp": timestamp,
            "title": title,
            "items": items
        }
    except Exception:
        return None

def fetch_leeks():
    for _ in range(len(RPC_ENDPOINTS)):
        url = get_rpc()
        payload = {
            "jsonrpc": "2.0", "id": 1, "method": "getProgramAccounts",
            "params": [
                PROGRAM_ID,
                {"encoding": "base64", "filters": [{"memcmp": {"offset": 0, "bytes": DISCRIMINATORS["leek"]}}, {"dataSize": 7156}]}
            ]
        }
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={"Content-Type": "application/json", "User-Agent": "CyberleekBot/1.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
                res = data.get("result", [])
                leeks = []
                for item in res:
                    raw = base64.b64decode(item["account"]["data"][0])
                    decoded = decode_leek(raw)
                    if decoded:
                        decoded["pubkey"] = item["pubkey"]
                        leeks.append(decoded)
                leeks.sort(key=lambda x: x["timestamp"], reverse=True)
                return leeks
        except Exception:
            switch_rpc()
    return []

def check_mirrors():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    results = []
    for u in MIRRORS:
        try:
            req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=4, context=ctx) as resp:
                status = "🟢" if resp.status == 200 else "🔴"
        except Exception:
            status = "🔴"
        results.append((status, u))
    return results

last_known_crypto = {"price": 0.0027, "mcap": 1950000.0, "vol24h": 370000.0, "change24h": 0.0}

def get_crypto_stats():
    global last_known_crypto
    # 1. GeckoTerminal (API Solana directe, pas de blocage)
    try:
        url = f"https://api.geckoterminal.com/api/v2/networks/solana/tokens/{TOKEN_ADDRESS}"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json'
        })
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode())
        attr = data.get("data", {}).get("attributes", {})
        price = float(attr.get("price_usd") or 0)
        mcap = float(attr.get("fdv_usd") or attr.get("market_cap_usd") or 0)
        vol24h = float(attr.get("volume_usd", {}).get("h24") or 0)
        if price > 0:
            last_known_crypto = {
                "price": price,
                "mcap": mcap,
                "vol24h": vol24h,
                "change24h": last_known_crypto.get("change24h", 0.0)
            }
            return last_known_crypto
    except Exception as e:
        pass

    # 2. DexScreener fallback
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{TOKEN_ADDRESS}"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json'
        })
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode())
        pairs = data.get("pairs") or []
        if pairs:
            pair = pairs[0]
            price = float(pair.get("priceUsd") or 0)
            mcap = float(pair.get("marketCap") or pair.get("fdv") or 0)
            vol24h = float(pair.get("volume", {}).get("h24") or 0)
            change24h = float(pair.get("priceChange", {}).get("h24") or 0)
            if price > 0:
                last_known_crypto = {
                    "price": price,
                    "mcap": mcap,
                    "vol24h": vol24h,
                    "change24h": change24h
                }
                return last_known_crypto
    except Exception as e:
        pass

    return last_known_crypto


def get_polls():
    for _ in range(len(RPC_ENDPOINTS)):
        url = get_rpc()
        payload = {
            'jsonrpc': '2.0', 'id': 1, 'method': 'getProgramAccounts',
            'params': [
                PROGRAM_ID,
                {'encoding': 'base64', 'filters': [{'memcmp': {'offset': 0, 'bytes': DISCRIMINATORS["poll"]}}]}
            ]
        }
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=8) as resp:
                res = json.loads(resp.read().decode())
            now = datetime.datetime.now(datetime.timezone.utc).timestamp()
            polls = []
            for item in res.get('result', []):
                raw = base64.b64decode(item['account']['data'][0])
                offset = 8 + 32 + 8 + 32
                l_title = struct.unpack_from('<I', raw, offset)[0]; offset += 4
                title = raw[offset:offset+l_title].decode('utf-8', errors='replace'); offset += l_title
                num_choices = struct.unpack_from('<I', raw, offset)[0]; offset += 4
                choices = []
                for _ in range(num_choices):
                    l_c = struct.unpack_from('<I', raw, offset)[0]; offset += 4
                    choices.append(raw[offset:offset+l_c].decode('utf-8', errors='replace')); offset += l_c
                ends_at = struct.unpack_from('<q', raw, offset)[0]; offset += 8
                cnt1 = struct.unpack_from('<I', raw, offset)[0]; offset += 4 + cnt1
                cnt2 = struct.unpack_from('<I', raw, offset)[0]; offset += 4
                votes = [struct.unpack_from('<Q', raw, offset + i*8)[0] for i in range(cnt2)]
                tot = sum(votes)
                status = "En cours" if ends_at > now else "Terminé"
                rem_sec = max(0, int(ends_at - now))
                if status == "En cours":
                    h = rem_sec // 3600
                    m = (rem_sec % 3600) // 60
                    countdown = f"{h}h {m}m"
                else:
                    countdown = "Expiré"
                
                choice_data = []
                for c, v in zip(choices, votes):
                    pct = (v / tot * 100) if tot else 0.0
                    choice_data.append({"choice": c, "pct": pct, "votes": v})

                polls.append({
                    "title": title,
                    "status": status,
                    "countdown": countdown,
                    "ends_at": ends_at,
                    "choices": choice_data
                })
            polls.sort(key=lambda x: (0 if x["status"] == "En cours" else 1, -x["ends_at"]))
            return polls
        except Exception:
            switch_rpc()
    return []

def capture_screenshot(leak=None, past_leeks=None):
    """Prend une VRAIE capture d'écran du navigateur réel sur le site Cyberleek via Chrome CDP."""
    t0 = time.time()
    try:
        js_script = os.path.join(SCRIPT_DIR, "take_real_screenshot.js")
        subprocess.run(["node", js_script], capture_output=True, timeout=25)
        real_out = os.path.join(SCRIPT_DIR, "real_live_website_screenshot.png")
        if os.path.exists(real_out) and os.path.getsize(real_out) > 1000:
            print(f"[Vraie Capture Réelle] Screenshot du site réel capturé en {time.time()-t0:.2f}s ({os.path.getsize(real_out)/1024:.1f} KB)", flush=True)
            return real_out
    except Exception as e:
        print(f"[Screenshot Error] {e}", flush=True)
    return None

def format_mirrors_message():
    mirror_lines = [
        "🌐 <b>STATUT DES MIROIRS ACTIFS</b>\n"
    ]
    mirrors = check_mirrors()
    for status, u in mirrors:
        domain = u.replace("https://", "").replace("/", "")
        mirror_lines.append(f"  {status} <code>{domain}</code>")
    fingerprint = tuple((s, u) for s, u in mirrors)
    return "\n".join(mirror_lines), fingerprint

def format_crypto_message():
    crypto = get_crypto_stats()
    ch_sign = "+" if crypto["change24h"] >= 0 else ""
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S UTC")
    crypto_lines = [
        "🪙 <b>STATUT DE LA CRYPTO $CYBERLEEK</b>\n",
        f"  • <b>Prix actuel :</b> <code>${crypto['price']:.6f}</code> ({ch_sign}{crypto['change24h']:.2f}% 24h)",
        f"  • <b>Market Cap :</b> <code>${crypto['mcap']:,.0f}</code>",
        f"  • <b>Volume 24h :</b> <code>${crypto['vol24h']:,.0f}</code>",
        f"\n<i>🔄 Mis à jour en direct : {now_str}</i>"
    ]
    fingerprint = (round(crypto['price'], 6), round(crypto['mcap'], 0), round(crypto['vol24h'], 0), round(crypto['change24h'], 2))
    return "\n".join(crypto_lines), fingerprint

def format_polls_message():
    try:
        proc = subprocess.run(["node", os.path.join(SCRIPT_DIR, "get_poll_data.js")], capture_output=True, text=True, timeout=10)
        p = json.loads(proc.stdout.strip())
        now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S UTC")

        poll_lines = [
            "📊 <b>TABLEAU DE BORD DES VOTES (MODE SILENCIEUX)</b>\n",
            f"🗳️ <b>Sujet :</b> {p['title']}",
            f"⏳ <b>Statut :</b> <code>{p['status']}</code> | Fin dans : <code>{p['countdown']}</code>"
        ]
        fingerprint = []
        for c in p["choices"]:
            poll_lines.append(f"  ▫️ {c['choice']} : <b>{c['pct']:.1f}%</b>")
            fingerprint.append((c['choice'], c['pct']))

        poll_lines.append("")
        poll_lines.append(f"<i>🔄 Mis à jour en direct : {now_str}</i>")
        return "\n".join(poll_lines), (p['title'], p['status'], p['countdown'], tuple(fingerprint))
    except Exception as e:
        print(f"[Erreur format_polls_message] {e}", flush=True)
        return "", None

def format_leak_message(leak):
    dt_str = datetime.datetime.fromtimestamp(leak['timestamp'], tz=datetime.timezone.utc).strftime("%d/%m/%Y à %H:%M UTC")
    leak_lines = [
        "🚨 <b>NOUVEAU LEEK DÉTECTÉ (SOURCE CYBERLEEK)</b> 🚨\n",
        f"🎯 <b>Nom du leak :</b> <code>{leak.get('title', 'Sans Titre')}</code>",
        f"📅 <b>Date :</b> {dt_str}\n",
        "📥 <b>Liens directs de téléchargement :</b>"
    ]
    items = leak.get("items", [])
    if items:
        for it in items:
            lbl = it.get("label", "Lien").strip()
            url = it.get("url", "").strip()
            leak_lines.append(f"  • <a href='{url}'>{lbl}</a>")
    else:
        leak_lines.append("  • <i>Aucun lien direct</i>")
    return "\n".join(leak_lines)

async def send_telegram_alert(client, channel, leak, past_leeks=None):
    seen = load_seen()
    active_msgs = seen.get("active_msgs", {})

    print(f"\n[ENVOI DE L'ALERTE LEEK] Publication du nouveau leak...", flush=True)

    # 1. INITIALISATION DES STATUTS PERMANENTS S'ILS N'EXISTENT PAS ENCORE
    if not active_msgs.get("mirrors") or not active_msgs.get("crypto") or not active_msgs.get("polls"):
        print("[Initialisation des messages de statut permanents...]", flush=True)
        try:
            mirrors_text, _ = format_mirrors_message()
            msg_mirrors = await client.send_message(channel, message=mirrors_text, parse_mode='html')
            active_msgs["mirrors"] = msg_mirrors.id
            await asyncio.sleep(0.4)

            crypto_text, _ = format_crypto_message()
            msg_crypto = await client.send_message(channel, message=crypto_text, parse_mode='html')
            active_msgs["crypto"] = msg_crypto.id
            await asyncio.sleep(0.4)

            polls_text, _ = format_polls_message()
            msg_polls = await client.send_message(channel, message=polls_text, parse_mode='html')
            active_msgs["polls"] = msg_polls.id
            await asyncio.sleep(0.4)
        except Exception as e:
            print(f"[Erreur init statuts] {e}", flush=True)
    else:
        try:
            c_text, _ = format_crypto_message()
            await client.edit_message(channel, active_msgs["crypto"], text=c_text, parse_mode='html')
        except Exception:
            pass
        try:
            p_text, _ = format_polls_message()
            await client.edit_message(channel, active_msgs["polls"], text=p_text, parse_mode='html')
        except Exception:
            pass

    # 2. ALERTE DU NOUVEAU LEEK (Nom exact + liens directs)
    msg_leak = None
    try:
        leak_text = format_leak_message(leak)
        msg_leak = await client.send_message(channel, message=leak_text, parse_mode='html')
        print(f"[Alerte leak envoyée avec succès] ID: {msg_leak.id}", flush=True)
    except Exception as e:
        print(f"[Erreur envoi leak] {e}", flush=True)

    # 3. SCREENSHOT AUTHENTIQUE DU SITE (Section ■ LEEKS, suit immédiatement le leak)
    msg_screen = None
    try:
        screen_path = await asyncio.to_thread(capture_screenshot, leak, past_leeks)
        if screen_path and os.path.exists(screen_path):
            screen_caption = (
                "📸 <b>Capture d'écran authentique du site (Section ■ LEEKS)</b>\n"
                f"🌐 <i>Source : https://cyberleek.saiph.weavegate.net/</i>"
            )
            msg_screen = await client.send_file(
                entity=channel,
                file=screen_path,
                caption=screen_caption,
                parse_mode='html',
                reply_to=msg_leak.id if msg_leak else None
            )
            print(f"[Screenshot authentique envoyé en suivi] ID: {msg_screen.id}", flush=True)
    except Exception as e:
        print(f"[Erreur envoi screenshot] {e}", flush=True)

    if msg_leak:
        active_msgs["leak"] = msg_leak.id
    if msg_screen:
        active_msgs["screen"] = msg_screen.id
    seen["active_msgs"] = active_msgs
    save_seen(seen)

async def monitor_loop():
    threading.Thread(target=start_health_server, daemon=True).start()
    print("=== DÉMARRAGE DU MONITOR CYBERLEEK AUTONOME ===", flush=True)
    seen = load_seen()

    client = TelegramClient('monitor_session', API_ID, API_HASH)
    await client.start(bot_token=BOT_TOKEN)
    channel = await client.get_entity(CHANNEL_ID)
    print(f"[Telegram] Connecté au canal: {channel.title} (ID: {channel.id})", flush=True)

    # Initialisation de base
    all_leeks = fetch_leeks()
    current_pks = [l["pubkey"] for l in all_leeks]
    if not seen.get("initialized", False):
        seen["leeks"] = current_pks
        seen["initialized"] = True
        save_seen(seen)
        print(f"[Init] Base synchronisée avec {len(all_leeks)} leeks existants.", flush=True)
    else:
        print(f"[Sync] {len(seen['leeks'])} leeks déjà connus en mémoire.", flush=True)

    active_msgs = seen.get("active_msgs", {})
    print(f"[Messages Actifs] Enregistrés: {active_msgs}", flush=True)

    print("[Surveillance] Écoute active on-chain (vérification ultra-rapide toutes les 1.5s)...", flush=True)
    print("[Dynamique] Modification in-place activée pour Crypto, Votes et Miroirs.\n", flush=True)

    last_crypto_check = 0
    last_polls_check = 0
    last_mirrors_check = 0
    
    last_crypto_fp = None
    last_polls_fp = None
    last_mirrors_fp = None

    while True:
        try:
            now = time.time()

            # 1. DÉTECTION ON-CHAIN ULTRA-RAPIDE (toutes les 1.5s)
            fresh_leeks = fetch_leeks()
            for lk in fresh_leeks:
                if lk["pubkey"] not in seen["leeks"]:
                    print(f"\n🚨 [NOUVEAU LEEK EN DIRECT DÉTECTÉ] : {lk.get('title')}", flush=True)
                    past = [p for p in fresh_leeks if p["pubkey"] != lk["pubkey"]]
                    # Envoi dans l'ordre (Leak et Screen en dernier)
                    await send_telegram_alert(client, channel, lk, past)
                    seen = load_seen()
                    seen["leeks"].append(lk["pubkey"])
                    save_seen(seen)
                    active_msgs = seen.get("active_msgs", {})

            # 2. MODIFICATION DYNAMIQUE DE LA CRYPTO (toutes les 20s)
            if now - last_crypto_check >= 20:
                last_crypto_check = now
                crypto_id = active_msgs.get("crypto")
                if crypto_id:
                    crypto_text, crypto_fp = format_crypto_message()
                    if crypto_fp != last_crypto_fp:
                        try:
                            await client.edit_message(channel, message=crypto_id, text=crypto_text, parse_mode='html')
                            last_crypto_fp = crypto_fp
                            print(f"[Crypto mis à jour dynamiquement] Message #{crypto_id} modifié (Prix: ${crypto_fp[0]:.6f})", flush=True)
                        except MessageNotModifiedError:
                            last_crypto_fp = crypto_fp
                        except Exception as e:
                            print(f"[Erreur edit crypto] {e}", flush=True)

            # 3. MODIFICATION DYNAMIQUE DES VOTES (toutes les 30s)
            if now - last_polls_check >= 30:
                last_polls_check = now
                polls_id = active_msgs.get("polls")
                if polls_id:
                    polls_text, polls_fp = format_polls_message()
                    if polls_fp != last_polls_fp:
                        try:
                            await client.edit_message(channel, message=polls_id, text=polls_text, parse_mode='html')
                            last_polls_fp = polls_fp
                            print(f"[Votes mis à jour dynamiquement] Message #{polls_id} modifié.", flush=True)
                        except MessageNotModifiedError:
                            last_polls_fp = polls_fp
                        except Exception as e:
                            print(f"[Erreur edit votes] {e}", flush=True)

            # 4. MODIFICATION DYNAMIQUE DES MIROIRS (toutes les 60s)
            if now - last_mirrors_check >= 60:
                last_mirrors_check = now
                mirrors_id = active_msgs.get("mirrors")
                if mirrors_id:
                    mirrors_text, mirrors_fp = format_mirrors_message()
                    if mirrors_fp != last_mirrors_fp:
                        try:
                            await client.edit_message(channel, message=mirrors_id, text=mirrors_text, parse_mode='html')
                            last_mirrors_fp = mirrors_fp
                            print(f"[Miroirs mis à jour dynamiquement] Message #{mirrors_id} modifié.", flush=True)
                        except MessageNotModifiedError:
                            last_mirrors_fp = mirrors_fp
                        except Exception as e:
                            print(f"[Erreur edit miroirs] {e}", flush=True)

            await asyncio.sleep(1.5)
        except Exception as e:
            print(f"[Erreur boucle monitor] {e}", flush=True)
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(monitor_loop())
