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
import urllib.parse
import ssl
import subprocess
import asyncio
import tempfile
import shutil
import zipfile
import re
import html
import http.cookiejar
import zlib
from telethon import TelegramClient, types, errors, events, Button
from telethon.sessions import StringSession
from telethon.errors import MessageNotModifiedError
from telethon.tl.functions.bots import SetBotCommandsRequest
from telethon.tl.types import BotCommand, BotCommandScopeDefault
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

class HealthHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        body = b"CYBERLEEK MONITOR ONLINE 24/7 OK"
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(body)

    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.send_header('Content-Length', '32')
        self.send_header('Connection', 'close')
        self.end_headers()

    def log_message(self, format, *args):
        pass

def start_health_server():
    port = int(os.environ.get("PORT", 10000))
    try:
        server = ThreadingHTTPServer(("0.0.0.0", port), HealthHandler)
        print(f"[HealthCheck] Serveur HTTP multithreadé actif sur le port {port} (pour Render / UptimeRobot)", flush=True)
        server.serve_forever()
    except Exception as e:
        print(f"[HealthCheck Notice] {e}", flush=True)


# Forcer UTF-8 sur Windows (supporte pythonw et services silencieux)
if sys.stdout is not None:
    try:
        if getattr(sys.stdout, 'encoding', None) != 'utf-8':
            sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
else:
    try:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
    except Exception:
        pass

# Credentials Telegram (supporte variables d'environnement pour Render)
API_ID = int(os.environ.get("TELEGRAM_API_ID", "32755876"))
API_HASH = os.environ.get("TELEGRAM_API_HASH", "d7c46be11bfc28c9825330b26310ceb0")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8985354063:AAHp-c4YNe0YI9Is0IeplCgXmz0c-wYsxDg")
TOKEN = BOT_TOKEN
CHANNEL_ID = int(os.environ.get("TELEGRAM_CHANNEL_ID", "-1003932229737"))
SESSION_STRING = os.environ.get("TELEGRAM_SESSION", "1BJWap1sBu25uEm8VyH6KA6h5pVGURJMc5AnAT-xMEyoxY3bRTOWy7RaLDNS230FtimEHrMZV2kLGYaNLFLY0JtEZb6dbRaijJFPS2a8VPcxneG3GSD7ss4vF1rvzdOJNeiRsxSEmZu7f74L0OHKsIbXxOZiex056xmOgFpCZiS2uF7YFek0bsMJR2NTWDWmPGLPekwrNMzH9EU2d4fW1O1vj7_4QYb6tAre-3KVMJcE6L4-yiBSoMYbxdukD0h8wDEqx76TK18nnjhacgyV2c8pXkwo-u77ThL6vSHzMzav6_ISS5fHvjLoXfFsuQmGjJ2iYr4UmRb0-hrq24pPI3YWwxeYsl7g=")



# Endpoints & Solana Protocol
SIMULATOR_MODE = "--sim" in sys.argv or "--simulator" in sys.argv or os.environ.get("SIMULATOR_MODE") == "1"
if SIMULATOR_MODE or os.environ.get("SOLANA_RPC_URL"):
    sim_port = os.environ.get("SIM_PORT", "8080")
    sim_rpc = os.environ.get("SOLANA_RPC_URL", f"http://localhost:{sim_port}/rpc")
    RPC_ENDPOINTS = [sim_rpc]
    print(f"⚡ [SIMULATOR MODE ACTIF] Connecté au clone local : {sim_rpc}", flush=True)
else:
    RPC_ENDPOINTS = [
        "https://api.mainnet-beta.solana.com",
        "https://public.rpc.solanavibestation.com",
        "https://solana.api.pocket.network"
    ]
current_rpc_idx = 0

PROGRAM_ID = "7rAgHPLDc9NryZmNdeEzyDui6D9PHkvTxMjKhNSa7w3a"
TOKEN_ADDRESS = "ApZuxdpzMrbEYTGEzeY9afh5pj9d6qPRJCTgQYiipbKg"

DISCRIMINATORS = {
    "leek": "G6JNBZ2BSey",         # Taille 7156
    "announcement": "NjkxTouaByo", # Taille 656
    "poll": "5Qpj1hsHT4k"          # Taille 2800
}


MIRRORS = [
    "https://cyberleek.ar.perma.online/",
    "https://wayfinder.vilenarios.com/?q=cyberleek",
    "https://cyberleek.saiph.weavegate.net/",
    "https://cyberleek.gatewaypie.com/"
]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SEEN_FILE = os.path.join(SCRIPT_DIR, "seen_leaks_tg.json")
STORAGE_DIR = os.path.join(SCRIPT_DIR, "saved_leaks")
os.makedirs(STORAGE_DIR, exist_ok=True)
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
    tmp_file = f"{SEEN_FILE}.tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_file, SEEN_FILE)

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

def decode_announcement(raw_bytes):
    try:
        reader = BinaryReader(raw_bytes[8:])
        authority = reader.bytes(32)
        timestamp = reader.i64()
        title = reader.str()
        body = reader.str()
        return {
            "timestamp": timestamp,
            "title": title,
            "body": body
        }
    except Exception:
        return None

def fetch_announcements():
    for _ in range(len(RPC_ENDPOINTS)):
        url = get_rpc()
        payload = {
            "jsonrpc": "2.0", "id": 1, "method": "getProgramAccounts",
            "params": [
                PROGRAM_ID,
                {"encoding": "base64", "filters": [{"memcmp": {"offset": 0, "bytes": DISCRIMINATORS["announcement"]}}]}
            ]
        }
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={"Content-Type": "application/json", "User-Agent": "CyberleekBot/1.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
                res = data.get("result", [])
                anns = []
                for item in res:
                    raw = base64.b64decode(item["account"]["data"][0])
                    decoded = decode_announcement(raw)
                    if decoded:
                        decoded["pubkey"] = item["pubkey"]
                        anns.append(decoded)
                anns.sort(key=lambda x: x["timestamp"])
                return anns
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
    try:
        if SIMULATOR_MODE:
            sim_port = os.environ.get("SIM_PORT", "8080")
            url = f"http://localhost:{sim_port}/dex/tokens/{TOKEN_ADDRESS}"
        else:
            url = os.environ.get("DEXSCREENER_URL") or f"https://api.dexscreener.com/latest/dex/tokens/{TOKEN_ADDRESS}"
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
    except Exception:
        pass

    # 2. GeckoTerminal fallback (si DexScreener est indisponible ou rate-limité)
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
    except Exception:
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
                pk = item.get('pubkey')
                raw = base64.b64decode(item['account']['data'][0])
                ts = struct.unpack_from('<q', raw, 8 + 32)[0]
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
                    "pubkey": pk,
                    "timestamp": ts,
                    "title": title,
                    "status": status,
                    "countdown": countdown,
                    "ends_at": ends_at,
                    "choices": choice_data
                })
            polls.sort(key=lambda x: (0 if x["status"] == "En cours" else 1, -x["timestamp"]))
            return polls
        except Exception:
            switch_rpc()
    return []

def capture_screenshot(section="content", leak=None, past_leeks=None, ann=None):
    """Prend une capture d'écran 100% réelle et authentique du site Cyberleek via Chrome headless CDP."""
    t0 = time.time()
    try:
        real_out = os.path.join(SCRIPT_DIR, "real_live_website_screenshot.png")
        if os.path.exists(real_out):
            try:
                os.remove(real_out)
            except Exception:
                pass
        js_script = os.path.join(SCRIPT_DIR, "take_real_screenshot.js")
        if os.path.exists(js_script):
            if SIMULATOR_MODE or os.environ.get("CYBERLEEK_SITE_URL"):
                sim_port = os.environ.get("SIM_PORT", "8080")
                active_url = os.environ.get("CYBERLEEK_SITE_URL", f"http://localhost:{sim_port}/")
            else:
                active_url = "https://cyberleek.gatewaypie.com/"
                try:
                    for status, u in check_mirrors():
                        if status == "🟢":
                            active_url = u
                            break
                except Exception:
                    pass

            subprocess.run(["node", js_script, section, active_url], capture_output=True, timeout=35)
            if os.path.exists(real_out) and os.path.getsize(real_out) > 1000:
                print(f"[Vraie Capture Réelle] Screenshot ({section}) capturé en {time.time()-t0:.2f}s ({os.path.getsize(real_out)/1024:.1f} KB)", flush=True)
                return real_out
    except Exception as e:
        print(f"[Screenshot Error] {e}", flush=True)

    return None

def update_last_channel_id(msg_id):
    try:
        if not msg_id: return
        current_seen = load_seen()
        cur_max = current_seen.get("last_channel_msg_id", 0)
        if msg_id > cur_max:
            current_seen["last_channel_msg_id"] = msg_id
            save_seen(current_seen)
    except Exception:
        pass

def register_pending_deletion(chat_id, msg_id, delay):
    try:
        current_seen = load_seen()
        if "pending_deletions" not in current_seen:
            current_seen["pending_deletions"] = []
        cid = getattr(chat_id, "id", chat_id)
        current_seen["pending_deletions"].append({
            "chat_id": cid,
            "msg_id": msg_id,
            "delete_at": time.time() + delay
        })
        save_seen(current_seen)
    except Exception as e:
        print(f"[Register Pending Deletion Notice] {e}", flush=True)

def remove_pending_deletion(msg_id):
    try:
        current_seen = load_seen()
        if "pending_deletions" in current_seen:
            current_seen["pending_deletions"] = [p for p in current_seen["pending_deletions"] if p.get("msg_id") != msg_id]
            save_seen(current_seen)
    except Exception:
        pass

async def delete_after_delay(client, channel, msg_id, delay=45):
    register_pending_deletion(channel, msg_id, delay)
    update_last_channel_id(msg_id)
    await asyncio.sleep(delay)
    try:
        target_entity = channel
        if isinstance(channel, int):
            try:
                target_entity = await client.get_entity(channel)
            except Exception:
                target_entity = channel
        await client.delete_messages(target_entity, msg_id)
        print(f"[Éphémère] Notification #{msg_id} supprimée après {delay}s.", flush=True)
    except Exception as e:
        print(f"[Erreur suppression notif #{msg_id}] {e}", flush=True)
    finally:
        remove_pending_deletion(msg_id)

async def process_pending_deletions(client, channel_entity):
    try:
        current_seen = load_seen()
        pending = current_seen.get("pending_deletions", [])
        if not pending:
            return
        now = time.time()
        to_delete = [p for p in pending if now >= p.get("delete_at", 0)]
        if not to_delete:
            return

        remaining = [p for p in pending if now < p.get("delete_at", 0)]
        for p in to_delete:
            cid = p.get("chat_id")
            mid = p.get("msg_id")
            try:
                if cid == CHANNEL_ID or cid == getattr(channel_entity, "id", None):
                    target = channel_entity
                elif isinstance(cid, int):
                    target = await client.get_entity(cid)
                else:
                    target = cid
                await client.delete_messages(target, mid)
                print(f"[Persistance] Nettoyage réussi du message orphelin #{mid}.", flush=True)
            except Exception:
                pass

        current_seen["pending_deletions"] = remaining
        save_seen(current_seen)
    except Exception as e:
        print(f"[Erreur process_pending_deletions] {e}", flush=True)

async def sanitize_channel(client, channel):
    try:
        current_seen = load_seen()
        active_ids = set(current_seen.get("active_msgs", {}).values())
        last_id = max(current_seen.get("last_channel_msg_id", 935), max(active_ids) if active_ids else 935)
        ids_to_check = list(range(max(1, last_id - 40), last_id + 5))
        msgs = await client.get_messages(channel, ids=ids_to_check)
        now = time.time()
        to_del = []
        for m in msgs:
            if not m:
                continue
            if m.id in active_ids:
                continue
            if m.media:
                continue
            txt = (m.raw_text or '').strip()
            age = now - m.date.timestamp()
            if txt.startswith('/'):
                to_del.append(m.id)
            elif any(txt.startswith(p) for p in ['🎯 Seuil Market Cap', '🤖 CYBERLEEK ALERTER BOT', '🔇 Alertes Market Cap', '🔔 Alertes Market Cap']):
                to_del.append(m.id)
            elif any(txt.startswith(p) for p in ['🪙 Nouveau palier atteint', '🪙 Baisse de palier']) and age > 50:
                to_del.append(m.id)
            elif txt.startswith('🗳️ CHANGEMENT DE LEADER') and age > 190:
                to_del.append(m.id)

        if to_del:
            await client.delete_messages(channel, to_del)
            print(f"[Sanitizer Canal] Suppression réussie de {len(to_del)} messages orphelins : {to_del}", flush=True)
    except Exception as e:
        print(f"[Sanitizer Canal Notice] {e}", flush=True)

def translate_to_fr(text):
    if not text:
        return ""
    try:
        clean_text = text.replace('leek', 'leak').replace('Leek', 'Leak').replace('LEEK', 'LEAK')
        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=fr&dt=t&q=" + urllib.parse.quote(clean_text)
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            translated = ''.join([item[0] for item in data[0] if item[0]])
            translated = translated.replace('poireau', 'fuite').replace('Poireau', 'Fuite').replace('POIREAU', 'FUITE')
            return translated
    except Exception as e:
        print(f"[Translation fallback] {e}", flush=True)
        return text

async def send_announcement_alert(client, channel, ann):
    tz_fr = datetime.timezone(datetime.timedelta(hours=2))
    dt_str = datetime.datetime.fromtimestamp(ann['timestamp'], tz=tz_fr).strftime("%d/%m/%Y à %H:%M (Paris)")
    
    title_en = html.escape(ann.get('title', 'Sans Titre'))
    body_en = html.escape(ann.get('body', ''))
    
    ann_lines = [
        "📢 <b>NOUVELLE ANNONCE OFFICIELLE CYBERLEEK</b>\n",
        f"🎯 <b>Titre :</b> <code>{title_en}</code>",
        f"📅 <b>Date :</b> {dt_str}\n",
        f"<blockquote>{body_en}</blockquote>"
    ]
    ann_text = "\n".join(ann_lines)
    
    print(f"\n[ANNONCE DÉTECTÉE] Publication de l'annonce '{title_en}'...", flush=True)
    screen_path = await asyncio.to_thread(capture_screenshot, "anns", ann=ann)
    if screen_path and os.path.exists(screen_path):
        caption = ann_text
        if len(caption) <= 1024:
            await client.send_file(channel, file=screen_path, caption=caption, parse_mode='html')
        else:
            msg_ann = await client.send_message(channel, message=ann_text, parse_mode='html')
            await client.send_file(channel, file=screen_path, parse_mode='html', reply_to=msg_ann.id)
    else:
        await client.send_message(channel, message=ann_text, parse_mode='html')
    print("  -> Annonce envoyée avec succès sur Telegram !", flush=True)

def get_paris_now():
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo("Europe/Paris"))
    except Exception:
        return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=2)))

def make_poll_bar(pct, length=20):
    filled = max(0, min(length, round(pct / (100 / length))))
    empty = length - filled
    return "█" * filled + "━" * empty

async def send_poll_alert(client, channel, poll):
    """Envoie une alerte officielle Telegram lorsqu'un nouveau vote communautaire est lancé sur Solana."""
    # Tenter d'enrichir avec get_poll_data.js pour avoir les pourcentages exacts
    if not any(c.get("pct", 0) > 0 for c in poll.get("choices", [])):
        try:
            js_p = os.path.join(SCRIPT_DIR, "get_poll_data.js")
            if os.path.exists(js_p):
                proc = subprocess.run(["node", js_p], capture_output=True, text=True, timeout=6)
                if proc.returncode == 0 and proc.stdout.strip():
                    p_js = json.loads(proc.stdout.strip())
                    if p_js.get("title") == poll.get("title") and p_js.get("choices"):
                        poll = p_js
        except Exception:
            pass

    now_str = get_paris_now().strftime("%H:%M:%S (Paris)")
    ends_at = poll.get('ends_at')
    if ends_at:
        tz_fr = datetime.timezone(datetime.timedelta(hours=2))
        end_dt = datetime.datetime.fromtimestamp(ends_at, tz=tz_fr)
        end_str = end_dt.strftime("%d/%m/%Y à %H:%M")
    else:
        end_str = "Inconnue"

    title_esc = html.escape(poll.get('title', 'Sujet inconnu'))
    countdown = poll.get('countdown', '')

    choices = poll.get("choices", [])
    leader_choice = max(choices, key=lambda c: (c.get("pct") or 0)).get("choice") if choices else None

    poll_lines = [
        "🗳️ <b>NOUVEAU VOTE OFFICIEL CYBERLEEK DÉTECTÉ</b> 🗳️\n",
        f"🗳️ <b>Sujet :</b> {title_esc}",
        f"⏳ <b>Statut :</b> En cours",
        f"📅 <b>Fin du vote :</b> {end_str} (dans {countdown})\n"
    ]

    for c in choices:
        ch_name = c.get("choice", "")
        ch_pct = float(c.get("pct") or 0.0)
        ch_name_esc = html.escape(ch_name)
        crown = "👑 " if ch_name == leader_choice and ch_pct > 0 else ""
        bar = make_poll_bar(ch_pct, length=20)
        poll_lines.append(f"{crown}<b>{ch_name_esc}</b>")
        poll_lines.append(f"{bar} {ch_pct:.1f}%\n")

    poll_lines.append(f"<i>🔄 Mis à jour en direct : {now_str}</i>")
    poll_text = "\n".join(poll_lines)
    print(f"\n[NOUVEAU VOTE DÉTECTÉ] Publication du vote '{title_esc}' sur Telegram...", flush=True)
    msg = await client.send_message(channel, message=poll_text, parse_mode='html')
    print(f"  -> Alerte nouveau vote envoyée avec succès (#{msg.id}) !", flush=True)
    return msg

def format_mirrors_message():
    mirror_lines = [
        "🌐 <b>STATUT DES MIROIRS ACTIFS</b>\n"
    ]
    mirrors = check_mirrors()
    for status, u in mirrors:
        domain = u.replace("https://", "").replace("/", "")
        mirror_lines.append(f'  {status} <a href="{u}"><b>{domain}</b></a>')
    mirror_lines.append("\n<i>👆 Cliquez directement sur un lien ou un bouton ci-dessous :</i>")
    fingerprint = tuple((s, u) for s, u in mirrors)
    return "\n".join(mirror_lines), fingerprint

def get_mirrors_buttons():
    btn_list = []
    for u in MIRRORS:
        if "gatewaypie" in u:
            lbl = "🌐 Gatewaypie"
        elif "perma" in u or "arweave" in u:
            lbl = "🌐 Arweave"
        elif "wayfinder" in u:
            lbl = "🌐 Wayfinder"
        elif "weavegate" in u or "saiph" in u:
            lbl = "🌐 Weavegate"
        else:
            lbl = "🌐 Miroir"
        btn_list.append(Button.url(lbl, u))
    rows = []
    for i in range(0, len(btn_list), 2):
        rows.append(btn_list[i:i+2])
    return rows

def format_crypto_message():
    crypto = get_crypto_stats()
    ch_sign = "+" if crypto["change24h"] >= 0 else ""
    now_str = get_paris_now().strftime("%H:%M:%S (Paris)")
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
    p = None
    if SIMULATOR_MODE:
        try:
            polls = get_polls()
            if polls:
                p = polls[0]
        except Exception:
            pass
    else:
        try:
            js_p = os.path.join(SCRIPT_DIR, "get_poll_data.js")
            if os.path.exists(js_p):
                proc = subprocess.run(["node", js_p], capture_output=True, text=True, timeout=10)
                if proc.returncode == 0 and proc.stdout.strip():
                    p = json.loads(proc.stdout.strip())
        except Exception:
            p = None

        # Fallback natif Python 100% autonome (utilise get_polls direct sur RPC Solana)
        if not p:
            try:
                polls = get_polls()
                if polls:
                    p = polls[0]
            except Exception as e_gp:
                print(f"[Fallback get_polls] {e_gp}", flush=True)

    if not p:
        return "", None

    try:
        now_str = get_paris_now().strftime("%H:%M:%S (Paris)")

        ends_at = p.get('ends_at')
        if ends_at:
            tz_fr = datetime.timezone(datetime.timedelta(hours=2))
            end_dt = datetime.datetime.fromtimestamp(ends_at, tz=tz_fr)
            end_str = end_dt.strftime("%d/%m/%Y à %H:%M")
        else:
            end_str = "Inconnue"

        p_title = html.escape(p.get('title', 'Sujet inconnu'))
        p_status = html.escape(p.get('status', 'Inconnu'))
        p_countdown = p.get('countdown', '')

        poll_lines = [
            "📊 <b>TABLEAU DE BORD DES VOTES (MODE SILENCIEUX)</b>\n",
            f"🗳️ <b>Sujet :</b> {p_title}",
            f"⏳ <b>Statut :</b> {p_status}",
            f"📅 <b>Fin du vote :</b> {end_str} (dans {p_countdown})\n"
        ]

        choices = p.get("choices", [])
        leader_choice = max(choices, key=lambda c: (c.get("pct") or 0)).get("choice") if choices else None

        fingerprint = []
        for c in choices:
            ch_name = c.get("choice", "")
            ch_pct = float(c.get("pct") or 0.0)
            ch_name_esc = html.escape(ch_name)
            crown = "👑 " if ch_name == leader_choice and ch_pct > 0 else ""
            bar = make_poll_bar(ch_pct, length=20)
            poll_lines.append(f"{crown}<b>{ch_name_esc}</b>")
            poll_lines.append(f"{bar} {ch_pct:.1f}%\n")
            fingerprint.append((ch_name, ch_pct))

        poll_lines.append(f"<i>🔄 Mis à jour en direct : {now_str}</i>")
        return "\n".join(poll_lines), (p.get('title', ''), p.get('status', ''), end_str, p_countdown, tuple(fingerprint), leader_choice, choices)

    except Exception as e:
        print(f"[Erreur format_polls_message] {e}", flush=True)
        return "", None

def format_leak_btn_label(lbl, url):
    lbl_lower = (lbl or "").lower()
    url_lower = (url or "").lower()
    if "arweave" in lbl_lower or "ar.io" in url_lower or "arweave.net" in url_lower:
        num = "".join(c for c in lbl_lower if c.isdigit())
        name = f"Arweave #{num}" if num else "Arweave"
    elif "bedrive" in lbl_lower or "bedrive.ru" in url_lower:
        name = "Bedrive"
    elif "temp.sh" in lbl_lower or "temp.sh" in url_lower:
        name = "Temp.sh"
    elif "upload.ee" in lbl_lower or "upload.ee" in url_lower:
        name = "Upload.ee"
    elif "transfiles" in lbl_lower or "transfiles.ru" in url_lower:
        name = "Transfiles"
    elif "gofile" in lbl_lower or "gofile.io" in url_lower:
        name = "Gofile"
    elif "disroot" in lbl_lower or "disroot.org" in url_lower:
        name = "Disroot"
    elif "lufi" in lbl_lower or "lufi.ethibox.fr" in url_lower:
        name = "Lufi"
    elif "krakenfiles" in lbl_lower or "krakenfiles.com" in url_lower:
        name = "Krakenfiles"
    elif "cyberleek" in lbl_lower or "cyberleek" in url_lower:
        name = "Cyberleek Mirror"
    else:
        parts = (lbl or "").strip().split()
        name = parts[0] if parts else "Miroir"
    return f"📥 {name} 📥"

def format_leak_message_and_buttons(leak):
    tz_fr = datetime.timezone(datetime.timedelta(hours=2))
    dt_str = datetime.datetime.fromtimestamp(leak['timestamp'], tz=tz_fr).strftime("%d/%m/%Y à %H:%M")

    raw_title = leak.get('title', 'Sans Titre')
    escaped_title = html.escape(raw_title)

    leak_lines = [
        "🚨 <b>NOUVEAU LEEK DÉTECTÉ</b> 🚨\n",
        f"🎯 <b>Nom du leak :</b> <code>{escaped_title}</code>",
        f"📅 <b>Date :</b> {dt_str}\n",
        "👇 -------<b>TÉLÉCHARGEMENT DIRECT</b>-------👇"
    ]

    buttons = []
    items = leak.get("items", [])
    for it in items:
        lbl = it.get("label", "Télécharger").strip()
        url = it.get("url", "").strip()
        if not url or not (url.startswith("http://") or url.startswith("https://")):
            continue
        btn_txt = format_leak_btn_label(lbl, url)
        btn_url = url
        if "localhost" in btn_url or "127.0.0.1" in btn_url:
            btn_url = "https://cyberleek.gatewaypie.com/"
        buttons.append(Button.url(btn_txt, btn_url))

    keyboard_rows = []
    for i in range(0, len(buttons), 2):
        keyboard_rows.append(buttons[i:i+2])

    return "\n".join(leak_lines), (keyboard_rows if keyboard_rows else None)

def format_leak_message(leak):
    text, _ = format_leak_message_and_buttons(leak)
    return text

def is_valid_binary_media_or_archive(file_path):
    """
    Vérifie rigoureusement qu'un fichier téléchargé est un binaire valide (vrai ZIP, vidéo, archive, image)
    et rejette catégoriquement toute page d'erreur HTML, suppression ou fichier corrompu.
    """
    if not file_path or not os.path.exists(file_path):
        return False, None
    try:
        size = os.path.getsize(file_path)
    except Exception:
        return False, None
    if size < 20:
        return False, None

    try:
        with open(file_path, 'rb') as f:
            header = f.read(2048)
        header_lower = header.lower()

        # 1. Rejet absolu si le fichier contient des balises HTML ou des messages d'erreur web
        if (b'<!doctype html' in header_lower or 
            b'<html' in header_lower or 
            b'<head' in header_lower or 
            b'<body' in header_lower or 
            b'<script' in header_lower or
            b'<div' in header_lower or
            b'<p>' in header_lower or
            b'download limit' in header_lower or
            b'not found' in header_lower or
            b'forbidden' in header_lower or
            b'\xd1\x84\xd0\xb0\xd0\xb9\xd0\xbb' in header_lower): # "файл"
            return False, "html"

        # 2. Vérification ZIP stricte (via zipfile.is_zipfile)
        if zipfile.is_zipfile(file_path):
            return True, "zip"

        # 3. Vérification des magic bytes d'archives ou médias
        if header.startswith(b'PK\x03\x04') or header.startswith(b'PK\x05\x06'):
            return True, "zip"
        if header.startswith(b'7z\xbc\xaf\x27\x1c'):
            return True, "7z"
        if header.startswith(b'Rar!\x1a\x07'):
            return True, "rar"
        if b'ftyp' in header[:32] or (header.startswith(b'\x00\x00\x00') and b'moov' in header[:64]):
            return True, "video"
        if header.startswith(b'\x1a\x45\xdf\xa3'): # MKV / WebM
            return True, "video"
        if header.startswith(b'RIFF') and b'AVI ' in header[:16]:
            return True, "video"
        if header.startswith(b'\xff\xd8\xff'): # JPEG
            return True, "image"
        if header.startswith(b'\x89PNG\r\n\x1a\n'): # PNG
            return True, "image"

        # 4. Si la taille est substantielle (> 50 KB) et sans aucune balise HTML
        if size > 50 * 1024 and not any(tag in header_lower for tag in [b'<html', b'<body', b'<!doctype', b'<title']):
            return True, "binary"
    except Exception:
        pass
    return False, None

def download_bedrive(url, dest):
    """
    Contourne automatiquement l'antibot de Bedrive.ru (résolution automatique
    du captcha couleur base64 et soumission du formulaire) pour télécharger le fichier.
    """
    try:
        ctx = ssl._create_unverified_context()
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), urllib.request.HTTPSHandler(context=ctx))
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        req = urllib.request.Request(url, headers=headers)
        resp = opener.open(req, timeout=20)
        raw_content = resp.read()
        html_preview = raw_content[:4096].decode('utf-8', errors='replace')
        if "antibot" in html_preview or "Button()" in html_preview:
            inputs = dict(re.findall(r'name=\\?"([^\\"]+)\\?" type=\\?"hidden\\?" value=\\?"([^\\"]*)\\?"', html_preview))
            img_match = re.search(r'data:image/png;base64,([A-Za-z0-9+/=]+)', html_preview)
            if img_match and inputs:
                raw_png = base64.b64decode(img_match.group(1))
                idat_idx = raw_png.find(b'IDAT')
                chunk_len = int.from_bytes(raw_png[idat_idx-4:idat_idx], 'big')
                decomp = zlib.decompress(raw_png[idat_idx+4:idat_idx+4+chunk_len])
                r, g, b = decomp[1], decomp[2], decomp[3]
                if r < 60 and g < 60 and b < 60:
                    color = "BLACK"
                elif r > 180 and g > 180 and b < 100:
                    color = "YELLOW"
                elif r > 180 and g < 100 and b < 100:
                    color = "RED"
                elif g > 150 and r < 100:
                    color = "GREEN"
                elif b > 150 and r < 100:
                    color = "BLUE"
                else:
                    color = "GRAY"
                post_data = inputs.copy()
                post_data['color'] = color
                post_req = urllib.request.Request(
                    url,
                    data=urllib.parse.urlencode(post_data).encode('utf-8'),
                    headers={**headers, 'Content-Type': 'application/x-www-form-urlencoded', 'Origin': 'https://bedrive.ru', 'Referer': url}
                )
                opener.open(post_req, timeout=20)
                file_req = urllib.request.Request(url, headers=headers)
                with opener.open(file_req, timeout=60) as file_resp, open(dest, 'wb') as f_out:
                    shutil.copyfileobj(file_resp, f_out)
        else:
            with open(dest, 'wb') as f_out:
                f_out.write(raw_content)

        if os.path.exists(dest):
            is_valid, kind = is_valid_binary_media_or_archive(dest)
            if is_valid:
                return True
            else:
                try:
                    os.remove(dest)
                except Exception:
                    pass
    except Exception as e:
        print(f"[Bedrive Downloader Notice] {e}", flush=True)
        if os.path.exists(dest):
            try:
                os.remove(dest)
            except Exception:
                pass
    return False

def download_tempsh(url, dest):
    """
    Télécharge automatiquement un fichier depuis Temp.sh en soumettant le formulaire POST requis.
    """
    try:
        ctx = ssl._create_unverified_context()
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), urllib.request.HTTPSHandler(context=ctx))
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': url,
            'Origin': 'https://temp.sh'
        }
        # 1. Vérification GET
        req_get = urllib.request.Request(url, headers=headers)
        with opener.open(req_get, timeout=15) as r_get:
            body = r_get.read(4096)
            if b'Download limit reached' in body or b'404 Not Found' in body:
                return False

        # 2. Requête POST pour déclencher le téléchargement du fichier
        req_post = urllib.request.Request(
            url,
            data=b'',
            headers={**headers, 'Content-Type': 'application/x-www-form-urlencoded'}
        )
        with opener.open(req_post, timeout=60) as resp, open(dest, 'wb') as f_out:
            shutil.copyfileobj(resp, f_out)

        if os.path.exists(dest):
            is_valid, kind = is_valid_binary_media_or_archive(dest)
            if is_valid:
                return True
            else:
                try: os.remove(dest)
                except Exception: pass
    except Exception as e:
        print(f"[Temp.sh Downloader Notice] {e}", flush=True)
        if os.path.exists(dest):
            try: os.remove(dest)
            except Exception: pass
    return False

async def repost_dashboards_at_bottom(client, channel):
    """
    Supprime et reposte immédiatement les 3 tableaux de bord permanents (Miroirs, Crypto, Sondage)
    au tout bas du canal pour maintenir une organisation parfaite après chaque alerte ou publication de leak.
    """
    try:
        cur_seen = load_seen()
        cur_active = cur_seen.get("active_msgs", {})
        old_to_del = [cur_active.get("mirrors"), cur_active.get("crypto"), cur_active.get("polls")]
        old_to_del = [i for i in old_to_del if i]
        if old_to_del:
            try:
                await client.delete_messages(channel, old_to_del)
            except Exception:
                pass

        m_text, _ = format_mirrors_message()
        new_m = await client.send_message(channel, m_text, buttons=get_mirrors_buttons(), link_preview=False, parse_mode='html')
        cur_active["mirrors"] = new_m.id
        await asyncio.sleep(0.3)

        c_text, _ = format_crypto_message()
        new_c = await client.send_message(channel, c_text, parse_mode='html')
        cur_active["crypto"] = new_c.id
        await asyncio.sleep(0.3)

        p_text, _ = format_polls_message()
        new_p = await client.send_message(channel, p_text, parse_mode='html')
        cur_active["polls"] = new_p.id

        cur_seen["active_msgs"] = cur_active
        save_seen(cur_seen)
        print(f"[Dashboards Repostés au bas du canal] Mirrors: #{new_m.id}, Crypto: #{new_c.id}, Polls: #{new_p.id}", flush=True)
    except Exception as e_rep:
        print(f"[Erreur Repost Dashboards] {e_rep}", flush=True)

async def process_and_send_leak_media(client, channel, leak, reply_to_id=None, auto_delete_delay=None):
    """
    Télécharge le fichier original du leak depuis les miroirs décentralisés (Arweave, Bedrive, etc.),
    extrait la vidéo sans compression si c'est un ZIP avec mot de passe, archive les fichiers
    dans notre base de données locale 'saved_leaks' et envoie le tout sur Telegram avec 100% de la
    qualité d'origine (bit par bit, sans aucune compression via force_document=True).
    Si auto_delete_delay est spécifié (pour les commandes comme /leaks), les fichiers envoyés s'auto-suppriment
    après ce délai (60s) pour préserver la propreté du chat.
    """
    title = leak.get("title", "Leak")
    pubkey = leak.get("pubkey", "unknown")
    leak_dir = os.path.join(STORAGE_DIR, pubkey)
    os.makedirs(leak_dir, exist_ok=True)

    pwd_match = re.search(r'(?:zip\s+)?password\s*:\s*([^\s,]+)', title, re.IGNORECASE)
    pwd = pwd_match.group(1) if pwd_match else None

    # 1. Vérification si les fichiers sont déjà archivés dans notre base de données locale
    saved_video = None
    saved_zip = None
    for root, _, files in os.walk(leak_dir):
        for f in sorted(files):
            full_p = os.path.join(root, f)
            if any(f.lower().endswith(ext) for ext in [".mp4", ".mkv", ".mov", ".webm", ".avi"]):
                is_valid, kind = is_valid_binary_media_or_archive(full_p)
                if is_valid and kind in ["video", "binary"]:
                    if not saved_video:
                        saved_video = full_p
                else:
                    try:
                        os.remove(full_p)
                    except Exception:
                        pass
            elif f.lower().endswith(".zip"):
                is_valid, kind = is_valid_binary_media_or_archive(full_p)
                if is_valid and kind == "zip":
                    if not saved_zip:
                        saved_zip = full_p
                else:
                    try:
                        os.remove(full_p)
                    except Exception:
                        pass

    # Si nous avons déjà les fichiers en base locale, les envoyer directement !
    if saved_video or saved_zip:
        print(f"[Media Leak] Fichiers trouvés dans la base locale pour '{title}'. Envoi direct...", flush=True)
        try:
            if saved_video and os.path.exists(saved_video):
                med_size_mb = os.path.getsize(saved_video) / (1024 * 1024)
                vid_cap = (
                    f"🎬 <b>Vidéo originale décompressée</b> : <code>{title}</code>\n"
                    f"📁 <i>Fichier : {os.path.basename(saved_video)} ({med_size_mb:.2f} Mo)</i>\n"
                    f"✨ <i>Qualité 100% brute d'origine (sans compression)</i>"
                )
                msg_v = await client.send_file(
                    channel,
                    file=saved_video,
                    caption=vid_cap,
                    parse_mode='html',
                    supports_streaming=True,
                    spoiler=True,
                    reply_to=reply_to_id
                )
                if auto_delete_delay:
                    asyncio.create_task(delete_after_delay(client, channel, msg_v.id, auto_delete_delay))

            if saved_zip and os.path.exists(saved_zip):
                zip_size_mb = os.path.getsize(saved_zip) / (1024 * 1024)
                zip_cap = (
                    f"📦 <b>Archive .ZIP originale du leak</b>\n"
                    f"📁 <i>Nom : {os.path.basename(saved_zip)} ({zip_size_mb:.2f} Mo)</i>"
                )
                if pwd:
                    zip_cap += f"\n🔑 <i>Mot de passe de l'archive :</i> <code>{pwd}</code>"
                msg_z = await client.send_file(
                    channel,
                    file=saved_zip,
                    caption=zip_cap,
                    parse_mode='html',
                    force_document=True,
                    reply_to=reply_to_id
                )
                if auto_delete_delay:
                    asyncio.create_task(delete_after_delay(client, channel, msg_z.id, auto_delete_delay))

            if not auto_delete_delay:
                await repost_dashboards_at_bottom(client, channel)
            return
        except Exception as e_cached:
            print(f"[Media Leak] Erreur envoi depuis base locale : {e_cached}", flush=True)

    # 2. Sinon, essayer de télécharger depuis les miroirs
    items = leak.get("items", [])
    if not items:
        if auto_delete_delay:
            err_msg = await client.send_message(
                channel,
                message="⚠️ <i>Aucun lien miroir disponible pour télécharger le fichier de ce leak.</i>",
                parse_mode='html',
                reply_to=reply_to_id
            )
            asyncio.create_task(delete_after_delay(client, channel, err_msg.id, auto_delete_delay))
        return

    candidate_urls = []
    for it in items:
        u = it.get("url", "").strip()
        if not u:
            continue
        u_lower = u.lower()
        if "localhost" in u_lower or "127.0.0.1" in u_lower:
            candidate_urls.insert(0, u)
        elif any(gw in u_lower for gw in ["arweave.net", "vilenarios.com", "turbo-gateway.com", "ar.io", "permaweb.app"]):
            candidate_urls.insert(0, u)
        elif any(u_lower.endswith(ext) for ext in [".mp4", ".zip", ".png", ".jpg", ".mkv", ".webm"]):
            candidate_urls.insert(0, u)
        else:
            candidate_urls.append(u)

    if not candidate_urls:
        return

    downloaded_file = None
    try:
        print(f"\n[Media Leak] Recherche & téléchargement pour : '{title}'...", flush=True)
        for u in candidate_urls:
            try:
                parsed_path = urllib.parse.urlparse(u).path
                base_name = os.path.basename(parsed_path) or f"leak_{pubkey[:8]}.bin"
                if base_name.endswith(".html"):
                    base_name = base_name[:-5]
                dest = os.path.join(leak_dir, base_name)

                print(f"[Media Leak] Essai de téléchargement depuis : {u}", flush=True)
                
                # Essai Bedrive si applicable
                if "bedrive.ru" in u.lower():
                    if download_bedrive(u, dest):
                        is_valid, kind = is_valid_binary_media_or_archive(dest)
                        if is_valid:
                            downloaded_file = dest
                            file_size_mb = os.path.getsize(dest) / (1024 * 1024)
                            print(f"[Media Leak] Téléchargement Bedrive réussi ({file_size_mb:.2f} Mo) [type: {kind}] !", flush=True)
                            break
                        else:
                            try:
                                os.remove(dest)
                            except Exception:
                                pass

                # Essai Temp.sh si applicable
                if "temp.sh" in u.lower():
                    if download_tempsh(u, dest):
                        is_valid, kind = is_valid_binary_media_or_archive(dest)
                        if is_valid:
                            downloaded_file = dest
                            file_size_mb = os.path.getsize(dest) / (1024 * 1024)
                            print(f"[Media Leak] Téléchargement Temp.sh réussi ({file_size_mb:.2f} Mo) [type: {kind}] !", flush=True)
                            break
                        else:
                            try:
                                os.remove(dest)
                            except Exception:
                                pass

                # Essai téléchargement HTTP direct
                req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
                with urllib.request.urlopen(req, timeout=45) as resp, open(dest, 'wb') as f_out:
                    shutil.copyfileobj(resp, f_out)

                if os.path.exists(dest):
                    is_valid, kind = is_valid_binary_media_or_archive(dest)
                    if not is_valid:
                        print(f"[Media Leak] Rejet du fichier téléchargé depuis {u} (fichier invalide ou page HTML).", flush=True)
                        try:
                            os.remove(dest)
                        except Exception:
                            pass
                        continue
                    downloaded_file = dest
                    file_size_mb = os.path.getsize(dest) / (1024 * 1024)
                    print(f"[Media Leak] Téléchargement réussi ({file_size_mb:.2f} Mo) [type: {kind}] !", flush=True)
                    break
            except Exception as e_dl:
                print(f"[Media Leak] Échec sur ce miroir ({u}) : {e_dl}", flush=True)
                if os.path.exists(dest):
                    try:
                        os.remove(dest)
                    except Exception:
                        pass

        if not downloaded_file:
            print("[Media Leak] Aucun fichier binaire valide n'a pu être téléchargé depuis les miroirs.", flush=True)
            mirror_links_text = ""
            if candidate_urls:
                valid_links = [f"• <a href='{u}'>{u[:55]}...</a>" if len(u) > 55 else f"• <a href='{u}'>{u}</a>" for u in candidate_urls[:4]]
                mirror_links_text = "\n\n🔗 <b>Liens directs des miroirs :</b>\n" + "\n".join(valid_links)
            notice_text = (
                f"⚠️ <b>Information média du leak :</b>\n"
                f"<i>Le fichier original (.zip ou vidéo) n'a pas pu être récupéré automatiquement "
                f"car les hébergeurs temporaires externes (Temp.sh, Bedrive, etc.) ont expiré ou supprimé l'archive.</i>"
                f"{mirror_links_text}"
            )
            err_msg = await client.send_message(
                channel,
                message=notice_text,
                parse_mode='html',
                reply_to=reply_to_id,
                link_preview=False
            )
            if auto_delete_delay:
                asyncio.create_task(delete_after_delay(client, channel, err_msg.id, auto_delete_delay))
            return

        is_valid, kind = is_valid_binary_media_or_archive(downloaded_file)
        is_zip = (kind == "zip")

        if is_zip:
            pwd_bytes = pwd.encode('utf-8') if pwd else None
            extracted_dir = os.path.join(leak_dir, "extracted")
            os.makedirs(extracted_dir, exist_ok=True)
            media_extracted = None

            try:
                with zipfile.ZipFile(downloaded_file, 'r') as zf:
                    if pwd_bytes:
                        zf.setpassword(pwd_bytes)
                    zf.extractall(extracted_dir)
            except Exception as e_zf:
                print(f"[Media Leak] zipfile natif ({e_zf}), essai avec outils système (7z/unzip)...", flush=True)
                if pwd:
                    subprocess.run(["7z", "x", f"-p{pwd}", f"-o{extracted_dir}", downloaded_file], capture_output=True)
                    subprocess.run(["unzip", "-P", pwd, downloaded_file, "-d", extracted_dir], capture_output=True)
                else:
                    subprocess.run(["7z", "x", f"-o{extracted_dir}", downloaded_file], capture_output=True)
                    subprocess.run(["unzip", downloaded_file, "-d", extracted_dir], capture_output=True)

            for root, _, files in os.walk(extracted_dir):
                for f in sorted(files):
                    f_full = os.path.join(root, f)
                    is_f_valid, f_kind = is_valid_binary_media_or_archive(f_full)
                    if is_f_valid and f_kind in ["video", "image", "binary"]:
                        media_extracted = f_full
                        break
                if media_extracted:
                    break

            # Enregistrer dans notre base de données seen_leaks_tg.json
            current_seen = load_seen()
            if "saved_leaks" not in current_seen:
                current_seen["saved_leaks"] = {}
            current_seen["saved_leaks"][pubkey] = {
                "title": title,
                "video_path": media_extracted,
                "zip_path": downloaded_file,
                "password": pwd,
                "timestamp": leak.get("timestamp")
            }
            save_seen(current_seen)

            if media_extracted and os.path.exists(media_extracted):
                med_size_mb = os.path.getsize(media_extracted) / (1024 * 1024)
                vid_cap = (
                    f"🎬 <b>Vidéo originale décompressée</b> : <code>{title}</code>\n"
                    f"📁 <i>Fichier : {os.path.basename(media_extracted)} ({med_size_mb:.2f} Mo)</i>\n"
                    f"✨ <i>Qualité 100% brute d'origine (sans compression)</i>"
                )
                print(f"[Media Leak] Envoi de la vidéo extraite sur Telegram...", flush=True)
                msg_v = await client.send_file(
                    channel,
                    file=media_extracted,
                    caption=vid_cap,
                    parse_mode='html',
                    supports_streaming=True,
                    spoiler=True,
                    reply_to=reply_to_id
                )
                if auto_delete_delay:
                    asyncio.create_task(delete_after_delay(client, channel, msg_v.id, auto_delete_delay))
                print("[Media Leak] Vidéo envoyée avec succès !", flush=True)

            zip_size_mb = os.path.getsize(downloaded_file) / (1024 * 1024)
            zip_cap = (
                f"📦 <b>Archive .ZIP originale du leak</b>\n"
                f"📁 <i>Nom : {os.path.basename(downloaded_file)} ({zip_size_mb:.2f} Mo)</i>"
            )
            if pwd:
                zip_cap += f"\n🔑 <i>Mot de passe de l'archive :</i> <code>{pwd}</code>"
            print(f"[Media Leak] Envoi de l'archive .ZIP originale sur Telegram...", flush=True)
            msg_z = await client.send_file(
                channel,
                file=downloaded_file,
                caption=zip_cap,
                parse_mode='html',
                force_document=True,
                reply_to=reply_to_id
            )
            if auto_delete_delay:
                asyncio.create_task(delete_after_delay(client, channel, msg_z.id, auto_delete_delay))
            print("[Media Leak] Archive .ZIP envoyée avec succès !", flush=True)

            if not auto_delete_delay:
                await repost_dashboards_at_bottom(client, channel)

        elif kind in ["video", "image", "binary"]:
            raw_size_mb = os.path.getsize(downloaded_file) / (1024 * 1024)
            file_cap = (
                f"🎬 <b>Fichier original du leak</b> : <code>{title}</code>\n"
                f"📁 <i>Fichier : {os.path.basename(downloaded_file)} ({raw_size_mb:.2f} Mo)</i>\n"
                f"✨ <i>Qualité 100% brute d'origine (sans compression)</i>"
            )
            print(f"[Media Leak] Envoi du fichier brut sur Telegram...", flush=True)
            if kind == "video":
                msg_raw = await client.send_file(
                    channel,
                    file=downloaded_file,
                    caption=file_cap,
                    parse_mode='html',
                    supports_streaming=True,
                    spoiler=True,
                    reply_to=reply_to_id
                )
            else:
                msg_raw = await client.send_file(
                    channel,
                    file=downloaded_file,
                    caption=file_cap,
                    parse_mode='html',
                    force_document=True,
                    reply_to=reply_to_id
                )
            if auto_delete_delay:
                asyncio.create_task(delete_after_delay(client, channel, msg_raw.id, auto_delete_delay))
            print("[Media Leak] Fichier original envoyé avec succès !", flush=True)

            current_seen = load_seen()
            if "saved_leaks" not in current_seen:
                current_seen["saved_leaks"] = {}
            current_seen["saved_leaks"][pubkey] = {
                "title": title,
                "video_path": downloaded_file,
                "zip_path": None,
                "password": pwd,
                "timestamp": leak.get("timestamp")
            }
            save_seen(current_seen)

            if not auto_delete_delay:
                await repost_dashboards_at_bottom(client, channel)

    except Exception as e_proc:
        print(f"[Erreur globale media leak] {e_proc}", flush=True)

async def send_telegram_alert(client, channel, leak, past_leeks=None):
    seen = load_seen()
    active_msgs = seen.get("active_msgs", {})

    print(f"\n[ENVOI DE L'ALERTE LEEK] Publication du nouveau leak...", flush=True)

    # 1. INITIALISATION DES STATUTS PERMANENTS S'ILS N'EXISTENT PAS ENCORE
    if not active_msgs.get("mirrors") or not active_msgs.get("crypto") or not active_msgs.get("polls"):
        print("[Initialisation des messages de statut permanents...]", flush=True)
        try:
            mirrors_text, _ = format_mirrors_message()
            msg_mirrors = await client.send_message(channel, message=mirrors_text, buttons=get_mirrors_buttons(), link_preview=False, parse_mode='html')
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

    # 2. ALERTE DU NOUVEAU LEEK (Nom exact + boutons directs)
    msg_leak = None
    try:
        leak_text, leak_buttons = format_leak_message_and_buttons(leak)
        msg_leak = await client.send_message(channel, message=leak_text, buttons=leak_buttons, parse_mode='html')
        print(f"[Alerte leak envoyée avec succès] ID: {msg_leak.id}", flush=True)
    except Exception as e:
        print(f"[Erreur envoi leak] {e}", flush=True)

    # 3. TÉLÉCHARGEMENT DIRECT ET ENVOI DE LA VIDÉO / DU FICHIER ORIGINAL (ET DU .ZIP)
    if msg_leak:
        active_msgs["leak"] = msg_leak.id
        asyncio.create_task(process_and_send_leak_media(client, channel, leak, reply_to_id=msg_leak.id))

    seen["active_msgs"] = active_msgs
    save_seen(seen)

async def monitor_loop():
    print("=== DÉMARRAGE DU MONITOR CYBERLEEK AUTONOME ===", flush=True)
    seen = load_seen()

    session = StringSession(SESSION_STRING) if SESSION_STRING else "bot_session"
    client = TelegramClient(session, API_ID, API_HASH)
    while True:
        try:
            await client.start(bot_token=BOT_TOKEN)
            break
        except Exception as e:
            if isinstance(e, errors.FloodWaitError):
                print(f"[Telegram FloodWait] Attente demandée par Telegram de {e.seconds}s...", flush=True)
                await asyncio.sleep(e.seconds + 2)
            else:
                print(f"[Telegram Connexion] {e}. Réessai dans 10s...", flush=True)
                await asyncio.sleep(10)

    channel = await client.get_entity(CHANNEL_ID)
    print(f"[Telegram] Connecté au canal: {channel.title} (ID: {channel.id})", flush=True)

    # 1. Enregistrement du menu officiel des commandes Telegram
    try:
        await client(SetBotCommandsRequest(
            scope=BotCommandScopeDefault(),
            lang_code='fr',
            commands=[
                BotCommand(command='help', description="Afficher l'aide et la liste des commandes"),
                BotCommand(command='crypto', description="Prix et Market Cap de $CYBERLEEK"),
                BotCommand(command='votes', description="Résultats du sondage GTA 6 en direct"),
                BotCommand(command='leaks', description="Dernier leak officiel Cyberleek"),
                BotCommand(command='mirrors', description="Statut des miroirs du site"),
                BotCommand(command='announcements', description="Dernière annonce officielle"),
                BotCommand(command='mcap', description="Muter ou configurer le seuil d'alerte Market Cap")
            ]
        ))
        print("[Telegram] Menu officiel des commandes configuré avec succès !", flush=True)
    except Exception as e_cmd:
        print(f"[Telegram Notice] Configuration commandes : {e_cmd}", flush=True)

    # 2. Gestionnaire interactif pour répondre à toutes les commandes (Auto-suppression après 1 min)
    @client.on(events.NewMessage)
    async def handle_bot_commands(event):
        raw = (event.message.raw_text or event.message.text or "").strip()

        async def handle_direct_leak_transfer(event):
            text = (event.message.raw_text or event.message.text or "").strip()
            has_media = bool(event.message.media)
            has_fwd = bool(event.message.fwd_from)

            url_matches = re.findall(r'https?://[^\s<>"]+', text)

            is_leak_submission = (
                has_media or 
                has_fwd or 
                bool(url_matches) or 
                any(k in text.lower() for k in ["gta", "leak", "leek", "cyberleek", "rockstar", "build", "footage", "video", "source", "password", "mega", "arweave", "temp.sh", "bedrive", "telecharger", "download"])
            )

            if not is_leak_submission and len(text) < 60:
                await event.reply(
                    "👋 <b>Bonjour !</b>\n\n"
                    "Pour publier un <b>nouveau leak</b> directement sur le canal officiel 🚨 Cyberleek Alerter 🚨 :\n"
                    "• 📁 <b>Envoie ou transfère-moi le fichier</b> (vidéo MP4, archive ZIP, document).\n"
                    "• 🔗 <b>Ou transfère-moi le message</b> contenant les détails et liens de téléchargement.\n"
                    "• 🔑 Si l'archive nécessite un mot de passe, indique-le dans ton message (ex: <code>password: mon_mdp</code>).\n\n"
                    "⚡ <i>Je m'occupe automatiquement d'extraire la vidéo en qualité 100% brute d'origine et de publier l'alerte sur le canal !</i>",
                    parse_mode='html'
                )
                return

            print(f"\n📥 [TRANSFERT DIRECT DE LEAK REÇU EN MP]", flush=True)
            print(f"  • Utilisateur ID: {event.sender_id}", flush=True)
            print(f"  • Texte: {text[:100]}", flush=True)
            print(f"  • Média: {has_media}, Transféré: {has_fwd}", flush=True)

            status_msg = await event.reply("⏳ <b>Nouveau leak reçu en transfert direct !</b>\n<i>Traitement du fichier et préparation de la publication sur le canal...</i>", parse_mode='html')

            # 1. Extraction du mot de passe si présent
            pwd_match = re.search(r'(?:zip\s+)?password\s*:\s*([^\s,]+)', text, re.IGNORECASE)
            pwd = pwd_match.group(1) if pwd_match else None

            # 2. Titre du leak
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            title = None
            for l in lines:
                if any(k in l.lower() for k in ["gta", "leak", "leek", "cyberleek", "build", "footage", "video", "source", "rockstar"]):
                    clean_l = re.sub(r'^(?:titre|title|leak|leek)\s*:\s*', '', l, flags=re.IGNORECASE).strip()
                    if clean_l:
                        title = clean_l
                        break
            if not title and lines:
                title = lines[0]
            if not title:
                f_name = getattr(event.message.file, 'name', None) if event.message.file else None
                title = f_name.replace('_', ' ').replace('-', ' ').rsplit('.', 1)[0] if f_name else "CYBERLEEK EXCLUSIVE LEAK"

            # 3. Liens trouvés dans le message
            items = []
            for u in url_matches:
                lbl = "Télécharger"
                if "bedrive" in u: lbl = "Bedrive Mirror"
                elif "temp.sh" in u: lbl = "Temp.sh Mirror"
                elif "arweave" in u or "ar.io" in u: lbl = "Arweave Mirror"
                elif "mega.nz" in u: lbl = "Mega Mirror"
                elif "gofile" in u: lbl = "Gofile Mirror"
                items.append({"label": lbl, "url": u})

            if not items:
                items = [{"label": "Direct Download", "url": "https://cyberleek.gatewaypie.com/"}]

            pubkey = f"Direct_{int(time.time())}_{event.sender_id}"
            leak_obj = {
                "title": title,
                "timestamp": int(time.time()),
                "items": items,
                "pubkey": pubkey
            }

            # 4. Dossier de stockage
            leak_dir = os.path.join(STORAGE_DIR, pubkey)
            os.makedirs(leak_dir, exist_ok=True)

            # 5. Si un média est joint directement dans le message Telegram
            downloaded_path = None
            if has_media:
                await status_msg.edit("📥 <i>Téléchargement du fichier Telegram en cours (qualité 100% originale)...</i>", parse_mode='html')
                downloaded_path = await client.download_media(event.message, file=leak_dir)
                print(f"[Direct Transfer] Fichier Telegram téléchargé : {downloaded_path}", flush=True)

                if downloaded_path and os.path.exists(downloaded_path):
                    # Si c'est un ZIP, décompresser
                    is_val, kind = is_valid_binary_media_or_archive(downloaded_path)
                    if kind == "zip" or downloaded_path.lower().endswith(".zip"):
                        await status_msg.edit("📦 <i>Archive ZIP détectée : Décompression automatique en cours...</i>", parse_mode='html')
                        extracted_dir = os.path.join(leak_dir, "extracted")
                        os.makedirs(extracted_dir, exist_ok=True)
                        pwd_bytes = pwd.encode('utf-8') if pwd else None
                        try:
                            with zipfile.ZipFile(downloaded_path, 'r') as zf:
                                if pwd_bytes: zf.setpassword(pwd_bytes)
                                zf.extractall(extracted_dir)
                        except Exception:
                            if pwd:
                                subprocess.run(["7z", "x", f"-p{pwd}", f"-o{extracted_dir}", downloaded_path], capture_output=True)
                            else:
                                subprocess.run(["7z", "x", f"-o{extracted_dir}", downloaded_path], capture_output=True)

            # 6. Publication de l'alerte sur le canal officiel
            await status_msg.edit("🚀 <i>Publication de l'alerte sur le canal 🚨 Cyberleek Alerter 🚨...</i>", parse_mode='html')
            msg_leak = None
            try:
                leak_text, leak_buttons = format_leak_message_and_buttons(leak_obj)
                msg_leak = await client.send_message(channel, message=leak_text, buttons=leak_buttons, parse_mode='html')
                active_msgs = load_seen().get("active_msgs", {})
                active_msgs["leak"] = msg_leak.id
                seen = load_seen()
                seen["active_msgs"] = active_msgs
                save_seen(seen)
                print(f"[Direct Transfer] Alerte envoyée sur le canal (ID: {msg_leak.id})", flush=True)
            except Exception as e_send:
                print(f"[Direct Transfer Alert Error] {e_send}", flush=True)

            if msg_leak:
                # Envoyer les médias en réponse directe
                await status_msg.edit("🎬 <i>Téléversement de la vidéo originale et de l'archive sur le canal...</i>", parse_mode='html')
                if has_media and (not downloaded_path or not downloaded_path.lower().endswith(".zip")):
                    med_size_mb = (os.path.getsize(downloaded_path) / (1024*1024)) if (downloaded_path and os.path.exists(downloaded_path)) else 0
                    vid_cap = (
                        f"🎬 <b>Vidéo originale décompressée</b> : <code>{title}</code>\n"
                        f"📁 <i>Fichier : {os.path.basename(downloaded_path) if downloaded_path else 'video.mp4'} ({med_size_mb:.2f} Mo)</i>\n"
                        f"✨ <i>Qualité 100% brute d'origine (sans compression)</i>"
                    )
                    await client.send_file(
                        channel,
                        file=event.message.media,
                        caption=vid_cap,
                        parse_mode='html',
                        supports_streaming=True,
                        spoiler=True,
                        reply_to=msg_leak.id
                    )
                    await repost_dashboards_at_bottom(client, channel)
                else:
                    await process_and_send_leak_media(client, channel, leak_obj, reply_to_id=msg_leak.id)

            # 7. Confirmation finale à l'utilisateur
            await status_msg.edit(
                f"✅ <b>LEAK PUBLIÉ AVEC SUCCÈS SUR LE CANAL !</b>\n\n"
                f"🎯 <b>Titre :</b> <code>{html.escape(title)}</code>\n"
                f"📢 <b>Canal :</b> {channel.title}\n"
                f"📁 <i>Le média haute qualité et l'alerte sont maintenant visibles par tous les abonnés du canal.</i>",
                parse_mode='html'
            )

        if not raw.startswith('/'):
            if event.is_private:
                try:
                    await handle_direct_leak_transfer(event)
                except Exception as e_transfer:
                    print(f"[Direct Transfer Error] {e_transfer}", flush=True)
            return

        # Normaliser les commandes avec espaces (ex: '/ mcap 7M', '/  crypto', etc.)
        clean_after_slash = raw[1:].lstrip()
        if not clean_after_slash:
            return
        norm_raw = '/' + clean_after_slash
        parts = norm_raw.split()
        cmd = parts[0].lower()
        if '@' in cmd:
            cmd = cmd.split('@')[0]

        async def reply_and_auto_delete(msg_text, buttons=None, delay=60):
            try:
                rep = await event.reply(msg_text, buttons=buttons, parse_mode='html')
                target = channel if event.chat_id == CHANNEL_ID else event.chat_id
                asyncio.create_task(delete_after_delay(client, target, rep.id, delay))
                asyncio.create_task(delete_after_delay(client, target, event.id, delay))
                return rep
            except Exception as e_rep:
                print(f"[Erreur envoi/auto-delete réponse] {e_rep}", flush=True)

        try:
            if cmd in ['/start', '/help']:
                help_text = (
                    "🤖 <b>CYBERLEEK ALERTER BOT</b> 🤖\n\n"
                    "Surveillance autonome 24h/24 du site Cyberleek et de la blockchain Solana.\n\n"
                    "📌 <b>Commandes disponibles :</b>\n"
                    "  • 🪙 /crypto - Cours, Market Cap et volume du token $CYBERLEEK\n"
                    "  • 📊 /votes - Résultats du sondage officiel GTA 6 et date de fin\n"
                    "  • 🚨 /leaks - Dernier leak officiel détecté avec liens directs\n"
                    "  • 🌐 /mirrors - Statut en direct des miroirs actifs du site\n"
                    "  • 📢 /announcements - Dernière annonce officielle Cyberleek\n"
                    "  • ⚙️ /mcap - Configurer ou rendre muettes les alertes Market Cap\n"
                    "  • ℹ️ /help - Afficher ce menu d'aide\n\n"
                    "⏱️ <i>Toutes les réponses de commandes s'auto-suppriment après 1 minute pour préserver l'ordre du chat.</i>"
                )
                await reply_and_auto_delete(help_text)

            elif cmd in ['/crypto', '/price']:
                c_text, _ = format_crypto_message()
                await reply_and_auto_delete(c_text)

            elif cmd in ['/votes', '/poll', '/polls']:
                p_text, _ = format_polls_message()
                await reply_and_auto_delete(p_text)

            elif cmd in ['/leaks', '/lastleak', '/leak']:
                all_l = fetch_leeks()
                if all_l:
                    all_l.sort(key=lambda x: x.get('timestamp', 0))
                    latest_leak = all_l[-1]
                    l_text, l_buttons = format_leak_message_and_buttons(latest_leak)
                    rep = await reply_and_auto_delete(l_text, buttons=l_buttons, delay=60)
                    asyncio.create_task(
                        process_and_send_leak_media(
                            client,
                            event.chat_id,
                            latest_leak,
                            reply_to_id=rep.id,
                            auto_delete_delay=60
                        )
                    )
                else:
                    await reply_and_auto_delete("Aucun leak détecté pour le moment.")

            elif cmd in ['/mirrors', '/status']:
                m_text, _ = format_mirrors_message()
                await reply_and_auto_delete(m_text, buttons=get_mirrors_buttons())

            elif cmd in ['/announcements', '/anns', '/news']:
                anns = fetch_announcements()
                if anns:
                    anns.sort(key=lambda x: x.get('timestamp', 0))
                    last_a = anns[-1]
                    tz_fr = datetime.timezone(datetime.timedelta(hours=2))
                    dt_str = datetime.datetime.fromtimestamp(last_a['timestamp'], tz=tz_fr).strftime("%d/%m/%Y à %H:%M (Paris)")
                    t_en = html.escape(last_a.get('title', 'Sans Titre'))
                    b_en = html.escape(last_a.get('body', ''))
                    a_lines = [
                        "📢 <b>DERNIÈRE ANNONCE OFFICIELLE CYBERLEEK</b>\n",
                        f"🎯 <b>Titre :</b> <code>{t_en}</code>",
                        f"📅 <b>Date :</b> {dt_str}\n",
                        f"<blockquote>{b_en}</blockquote>"
                    ]
                    await reply_and_auto_delete("\n".join(a_lines))
                else:
                    await reply_and_auto_delete("Aucune annonce officielle disponible pour le moment.")

            elif cmd in ['/mcap', '/marketcap']:
                args_str = " ".join(parts[1:]).strip().lower()
                current_seen = load_seen()

                # 1. Mute / Silence complet
                if args_str in ['mute', 'off', 'silence', 'silencieux', 'desactiver', 'désactiver', 'couper', 'stop']:
                    current_seen["mcap_muted"] = True
                    save_seen(current_seen)
                    resp_text = (
                        "🔇 <b>Alertes Market Cap désactivées (Mode Muet)</b>\n\n"
                        "Le bot n'enverra plus aucune notification de palier de Market Cap.\n"
                        "💡 <i>Pour réactiver :</i> <code>/mcap on</code> <i>ou définir un seuil avec</i> <code>/mcap 7M</code>."
                    )
                    await reply_and_auto_delete(resp_text, delay=60)

                # 2. Réactiver toutes les alertes (seuil remis à 0)
                elif args_str in ['on', 'unmute', 'enable', 'activer', 'reset']:
                    current_seen["mcap_muted"] = False
                    current_seen["mcap_min_threshold"] = 0
                    save_seen(current_seen)
                    resp_text = (
                        "🔔 <b>Alertes Market Cap réactivées</b>\n\n"
                        "Le bot notifiera chaque palier standard ($1M, $2M, $3M...) en hausse et en baisse.\n"
                        "💡 <i>Pour filtrer en dessous d'un montant :</i> <code>/mcap 7M</code>"
                    )
                    await reply_and_auto_delete(resp_text, delay=60)

                # 3. Chiffre ou montant spécifié (ex: 7M, 7m, 7 M, 7, 7.5M, 10M, 0)
                else:
                    num_match = re.search(r'(\d+(?:[\.,]\d+)?)', args_str)
                    if num_match:
                        raw_num = float(num_match.group(1).replace(',', '.'))
                        if raw_num <= 0:
                            current_seen["mcap_muted"] = False
                            current_seen["mcap_min_threshold"] = 0
                            save_seen(current_seen)
                            resp_text = (
                                "🔔 <b>Seuil réinitialisé (Tous les paliers actifs)</b>\n\n"
                                "Le bot notifiera tous les paliers standard ($1M, $2M, $3M...).\n"
                                "💡 <i>Pour filtrer en dessous d'un montant :</i> <code>/mcap 7M</code>"
                            )
                            await reply_and_auto_delete(resp_text, delay=60)
                        else:
                            if raw_num >= 100_000:
                                thresh_val = int(raw_num)
                                display_m = round(thresh_val / 1_000_000, 2)
                            else:
                                thresh_val = int(raw_num * 1_000_000)
                                display_m = int(raw_num) if raw_num.is_integer() else raw_num

                            current_seen["mcap_muted"] = False
                            current_seen["mcap_min_threshold"] = thresh_val
                            save_seen(current_seen)
                            resp_text = (
                                f"🎯 <b>Seuil Market Cap configuré : ${display_m}M</b>\n\n"
                                f"✅ Les alertes sont désormais <b>désactivées en dessous de ${display_m}M</b>.\n"
                                f"Le bot restera silencieux et n'enverra de notifications qu'à partir de <b>${display_m}M de Market Cap</b> !"
                            )
                            await reply_and_auto_delete(resp_text, delay=60)

                    # 4. Aucun argument valide -> Statut actuel et instructions
                    else:
                        is_muted = current_seen.get("mcap_muted", False)
                        min_t_raw = current_seen.get("mcap_min_threshold", 0)
                        min_t_m = min_t_raw / 1_000_000
                        display_cur_m = int(min_t_m) if min_t_m.is_integer() else min_t_m

                        if is_muted:
                            st_desc = "🔇 <b>Mode Muet activé</b> (Aucune alerte de palier envoyée)"
                        elif min_t_raw > 0:
                            st_desc = f"🎯 <b>Seuil actif : ${display_cur_m}M</b> (Désactivé sous ${display_cur_m}M, notifications dès ${display_cur_m}M)"
                        else:
                            st_desc = "🔔 <b>Actif standard</b> (Alertes pour tous les paliers $1M, $2M, $3M...)"

                        status_text = (
                            "🪙 <b>CONFIGURATION DES ALERTES MARKET CAP</b>\n\n"
                            f"• <b>Statut actuel :</b> {st_desc}\n\n"
                            "💡 <b>Commandes disponibles :</b>\n"
                            "  • <code>/mcap 7M</code> : Couper les alertes en dessous de 7 Millions\n"
                            "  • <code>/mcap mute</code> : Couper complètement toutes les alertes\n"
                            "  • <code>/mcap on</code> : Réactiver tous les paliers standards\n\n"
                            "<i>Note : Les commandes avec espace (ex: <code>/ mcap 7M</code>) sont également supportées.</i>"
                        )
                        await reply_and_auto_delete(status_text, delay=60)

        except Exception as e_h:
            print(f"[Erreur commande {cmd}] {e_h}", flush=True)


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
    last_sanitize_check = 0
    
    last_crypto_fp = None
    last_polls_fp = None
    last_mirrors_fp = None

    while True:
        try:
            now = time.time()

            # 0. GESTION PERSISTANTE DES SUPPRESSIONS ÉPHÉMÈRES (toutes les 1.5s)
            await process_pending_deletions(client, channel)

            # 1. DÉTECTION ON-CHAIN ULTRA-RAPIDE (toutes les 1.5s)
            # 1. DÉTECTION ON-CHAIN DES LEAKS (toutes les 1.5s)
            fresh_leeks = fetch_leeks()
            for lk in fresh_leeks:
                if lk["pubkey"] not in seen.get("leeks", []):
                    print(f"\n🚨 [NOUVEAU LEEK EN DIRECT DÉTECTÉ] : {lk.get('title')}", flush=True)
                    past = [p for p in fresh_leeks if p["pubkey"] != lk["pubkey"]]
                    await send_telegram_alert(client, channel, lk, past)
                    seen = load_seen()
                    seen["leeks"].append(lk["pubkey"])
                    save_seen(seen)
                    active_msgs = seen.get("active_msgs", {})

            # 2. DÉTECTION ON-CHAIN DES ANNONCES DU SITE (toutes les 1.5s)
            fresh_anns = fetch_announcements()
            seen_anns = set(seen.get("announcements", []))
            for ann in fresh_anns:
                if ann["pubkey"] not in seen_anns:
                    await send_announcement_alert(client, channel, ann)
                    seen = load_seen()
                    if "announcements" not in seen:
                        seen["announcements"] = []
                    seen["announcements"].append(ann["pubkey"])
                    save_seen(seen)
                    seen_anns.add(ann["pubkey"])

            # 2.5 DÉTECTION ON-CHAIN DES NOUVEAUX VOTES DU SITE (toutes les 1.5s)
            fresh_polls = get_polls()
            seen_polls = set(seen.get("polls", []))
            for pl in fresh_polls:
                pk = pl.get("pubkey") or pl.get("title")
                if pl.get("status") == "En cours" and pk not in seen_polls:
                    print(f"\n🗳️ [NOUVEAU VOTE EN DIRECT DÉTECTÉ] : {pl.get('title')}", flush=True)
                    await send_poll_alert(client, channel, pl)
                    seen = load_seen()
                    if "polls" not in seen:
                        seen["polls"] = []
                    seen["polls"].append(pk)
                    save_seen(seen)
                    seen_polls.add(pk)

            # 3. MODIFICATION DYNAMIQUE DE LA CRYPTO ET PALIERS MCAP (toutes les 20s)
            if now - last_crypto_check >= 20:
                last_crypto_check = now
                crypto_id = active_msgs.get("crypto")
                if crypto_id:
                    crypto_text, crypto_fp = format_crypto_message()
                    if crypto_text and crypto_fp and crypto_fp != last_crypto_fp:
                        try:
                            await client.edit_message(channel, message=crypto_id, text=crypto_text, parse_mode='html')
                            last_crypto_fp = crypto_fp
                            print(f"[Crypto mis à jour dynamiquement] Message #{crypto_id} modifié (Prix: ${crypto_fp[0]:.6f})", flush=True)
                        except MessageNotModifiedError:
                            last_crypto_fp = crypto_fp
                        except Exception as e:
                            print(f"[Erreur edit crypto] {e}", flush=True)

                # Vérification des changements de paliers de Market Cap (hausse ou baisse, notif éphémère de 45s)
                try:
                    current_seen = load_seen()
                    # Si le mode muet est activé, ne pas envoyer de notification
                    if current_seen.get("mcap_muted", False):
                        pass
                    else:
                        min_thresh = current_seen.get("mcap_min_threshold", 0)
                        c_stats = get_crypto_stats()
                        c_mcap = c_stats.get("mcap", 0)
                        mcap_steps = [1_000_000, 2_000_000, 3_000_000, 4_000_000, 5_000_000, 6_000_000, 7_000_000, 8_000_000, 9_000_000, 10_000_000, 15_000_000, 20_000_000, 25_000_000, 30_000_000]
                        
                        # Déterminer le palier actuel atteint
                        current_step = 0
                        for s in mcap_steps:
                            if c_mcap >= s:
                                current_step = s
                            else:
                                break
                                
                        last_step = current_seen.get("current_mcap_level")
                        if last_step is None:
                            last_step = current_step
                            current_seen["current_mcap_level"] = last_step
                            save_seen(current_seen)
                        
                        # 1. NOUVEAU PALIER ATTEINT EN HAUSSE (Uniquement si >= seuil minimum)
                        if current_step > last_step and current_step > 0:
                            current_seen["current_mcap_level"] = current_step
                            save_seen(current_seen)
                            should_alert_up = (min_thresh == 0 and current_step > 0) or (min_thresh > 0 and current_step >= min_thresh)
                            if should_alert_up:
                                ms_millions = current_step // 1_000_000
                                ms_notif = f"🪙 Nouveau palier atteint : <b>${ms_millions}M de Market Cap</b> ! 🚀"
                                sent_ms = await client.send_message(channel, message=ms_notif, parse_mode='html')
                                print(f"[Palier Mcap Hausse] Notification envoyée (#{sent_ms.id}) : ${ms_millions}M. Suppression dans 45s...", flush=True)
                                asyncio.create_task(delete_after_delay(client, channel, sent_ms.id, 45))
                            
                        # 2. BAISSE DE PALIER (Uniquement si >= seuil minimum)
                        elif last_step > 0 and c_mcap < (last_step - 50_000):
                            current_seen["current_mcap_level"] = current_step
                            save_seen(current_seen)
                            should_alert_down = (min_thresh == 0) or (min_thresh > 0 and current_step >= min_thresh and current_step > 0)
                            if should_alert_down:
                                if current_step > 0:
                                    curr_millions = current_step // 1_000_000
                                    down_notif = f"🪙 Baisse de palier : <b>Retour à ${curr_millions}M de Market Cap</b> ! 🔻"
                                else:
                                    down_notif = "🪙 Baisse de palier : <b>Passage sous les $1M de Market Cap</b> ! 🔻"
                                sent_down = await client.send_message(channel, message=down_notif, parse_mode='html')
                                print(f"[Palier Mcap Baisse] Notification envoyée (#{sent_down.id}) : Retour à ${current_step//1_000_000}M. Suppression dans 45s...", flush=True)
                                asyncio.create_task(delete_after_delay(client, channel, sent_down.id, 45))

                except Exception as e:
                    print(f"[Erreur check palier mcap] {e}", flush=True)

            # 4. MODIFICATION DYNAMIQUE DES VOTES ET DÉPASSEMENT DE LEADER (toutes les 30s)
            if now - last_polls_check >= 30:
                last_polls_check = now
                polls_id = active_msgs.get("polls")
                polls_text, poll_data = format_polls_message()
                if polls_id and polls_text and poll_data:
                    polls_fp = poll_data[:5]
                    if polls_fp != last_polls_fp:
                        try:
                            await client.edit_message(channel, message=polls_id, text=polls_text, parse_mode='html')
                            last_polls_fp = polls_fp
                            print(f"[Votes mis à jour dynamiquement] Message #{polls_id} modifié.", flush=True)
                        except MessageNotModifiedError:
                            last_polls_fp = polls_fp
                        except Exception as e:
                            print(f"[Erreur edit votes] {e}", flush=True)

                    # Vérification de renversement de leader dans le vote sans relancer de subprocess
                    try:
                        p_title = poll_data[0] if len(poll_data) > 0 else ""
                        current_lead = poll_data[5] if len(poll_data) > 5 else None
                        p_choices = poll_data[6] if len(poll_data) > 6 else []
                        last_lead = seen.get("last_poll_leader")
                        last_poll_title = seen.get("current_poll_title")
                        has_votes = any(c.get("pct", 0) > 0 for c in p_choices)

                        # Si le titre du sondage a changé, mettre à jour le titre actuel sans fausse alerte de flip
                        if p_title and last_poll_title != p_title:
                            seen["current_poll_title"] = p_title
                            seen["last_poll_leader"] = current_lead if has_votes else None
                            save_seen(seen)
                        elif has_votes and last_lead and current_lead and current_lead != last_lead:
                            flip_lines = [
                                "🗳️ <b>CHANGEMENT DE LEADER DANS LE VOTE GTA 6 !</b> 🗳️\n",
                                f"🔥 <b>{html.escape(current_lead)}</b> vient de devancer <b>{html.escape(last_lead)}</b> !\n",
                                "📊 <b>Nouveaux résultats :</b>\n"
                            ]
                            for c in p_choices:
                                ch_name = c.get("choice", "")
                                ch_pct = float(c.get("pct") or 0.0)
                                crown = "👑 " if ch_name == current_lead else ""
                                bar = make_poll_bar(ch_pct, length=20)
                                flip_lines.append(f"{crown}<b>{html.escape(ch_name)}</b>")
                                flip_lines.append(f"{bar} {ch_pct:.1f}%\n")
                            flip_text = "\n".join(flip_lines)
                            sent_flip = await client.send_message(channel, message=flip_text, parse_mode='html')
                            asyncio.create_task(delete_after_delay(client, channel, sent_flip.id, 180))
                            seen["last_poll_leader"] = current_lead
                            save_seen(seen)
                        elif has_votes and not last_lead and current_lead:
                            seen["last_poll_leader"] = current_lead
                            save_seen(seen)
                    except Exception as e:
                        pass

            # 5. MODIFICATION DYNAMIQUE DES MIROIRS (toutes les 60s)
            if now - last_mirrors_check >= 60:
                last_mirrors_check = now
                mirrors_id = active_msgs.get("mirrors")
                if mirrors_id:
                    mirrors_text, mirrors_fp = format_mirrors_message()
                    if mirrors_text and mirrors_fp and mirrors_fp != last_mirrors_fp:
                        try:
                            await client.edit_message(channel, message=mirrors_id, text=mirrors_text, buttons=get_mirrors_buttons(), link_preview=False, parse_mode='html')
                            last_mirrors_fp = mirrors_fp
                            print(f"[Miroirs mis à jour dynamiquement] Message #{mirrors_id} modifié.", flush=True)
                        except MessageNotModifiedError:
                            last_mirrors_fp = mirrors_fp
                        except Exception as e:
                            print(f"[Erreur edit miroirs] {e}", flush=True)

            # 6. BALAYAGE DE SÉCURITÉ DU CANAL (toutes les 60s)
            if now - last_sanitize_check >= 60:
                last_sanitize_check = now
                await sanitize_channel(client, channel)

            await asyncio.sleep(1.5)
        except Exception as e:
            print(f"[Erreur boucle monitor] {e}", flush=True)
            await asyncio.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=start_health_server, daemon=True).start()
    asyncio.run(monitor_loop())

