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
        clean_path = self.path.split('?')[0].rstrip('/')
        if not clean_path:
            clean_path = '/'

        if clean_path in ['/health', '/ping']:
            body = b"CYBERLEEK MONITOR ONLINE 24/7 OK"
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(body)
            return

        elif clean_path == '/api/stats':
            try:
                crypto = get_crypto_stats()
                p_text, p_alert = format_polls_message()
                poll_info = None
                if p_alert and len(p_alert) >= 5:
                    choices = p_alert[4]
                    if choices:
                        leader_choice, leader_pct = choices[0]
                        poll_info = {
                            "title": p_alert[0],
                            "status": p_alert[1],
                            "countdown": p_alert[3],
                            "leader": leader_choice,
                            "pct": leader_pct
                        }
                data = {
                    "crypto": crypto,
                    "poll": poll_info,
                    "mirrors": [{"status": s, "url": u} for s, u in check_mirrors()]
                }
                body = json.dumps(data, ensure_ascii=False).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Connection', 'close')
                self.end_headers()
                self.wfile.write(body)
                return
            except Exception as e:
                err_b = json.dumps({"error": str(e)}).encode('utf-8')
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(err_b)))
                self.send_header('Connection', 'close')
                self.end_headers()
                self.wfile.write(err_b)
                return

        elif clean_path == '/api/leaks':
            hub_json_path = os.path.join(SCRIPT_DIR, "leaks_database.json")
            if os.path.exists(hub_json_path):
                with open(hub_json_path, 'rb') as f:
                    body = f.read()
            else:
                body = b"[]"
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(body)
            return

        elif clean_path == '/mascot.png':
            mascot_file = os.path.join(SCRIPT_DIR, "mascot.png")
            if os.path.exists(mascot_file):
                with open(mascot_file, 'rb') as f:
                    body = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'image/png')
                self.send_header('Content-Length', str(len(body)))
                self.send_header('Connection', 'close')
                self.end_headers()
                self.wfile.write(body)
                return

        # Par défaut : servir le Hub GTA 6 (Mini App)
        hub_path = os.path.join(SCRIPT_DIR, "hub.html")
        if os.path.exists(hub_path):
            with open(hub_path, 'rb') as f:
                body = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(body)
        else:
            body = b"CYBERLEEK MONITOR ONLINE 24/7 OK"
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(body)

    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', '32')
        self.send_header('Connection', 'close')
        self.end_headers()

    def log_message(self, format, *args):
        pass

def start_health_server():
    port = int(os.environ.get("PORT", 10000))
    try:
        server = ThreadingHTTPServer(("0.0.0.0", port), HealthHandler)
        print(f"[HealthCheck] Serveur HTTP multithreadé actif sur le port {port} (pour Render / UptimeRobot / Mini App)", flush=True)
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
TOKEN = BOT_TOKEN
CHANNEL_ID = int(os.environ.get("TELEGRAM_CHANNEL_ID", "-1003932229737"))
SESSION_STRING = os.environ.get("TELEGRAM_SESSION", "")



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
    "leek": "G6JNBZ2BSey",         # Taille 7156
    "announcement": "NjkxTouaByo", # Taille 656
    "poll": "5Qpj1hsHT4k"          # Taille 2800
}


MIRRORS = [
    "https://cyberleek.ar.perma.online/",
    "https://wayfinder.vilenarios.com/?q=cyberleek",
    "https://cyberleek.saiph.weavegate.net/"
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

def capture_screenshot(section="content", leak=None, past_leeks=None):
    """Prend une VRAIE capture d'écran du navigateur réel sur le site Cyberleek via Chrome CDP."""
    t0 = time.time()
    try:
        real_out = os.path.join(SCRIPT_DIR, "real_live_website_screenshot.png")
        if os.path.exists(real_out):
            try:
                os.remove(real_out)
            except Exception:
                pass
        js_script = os.path.join(SCRIPT_DIR, "take_real_screenshot.js")
        subprocess.run(["node", js_script, section], capture_output=True, timeout=30)
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
    
    title_en = ann.get('title', 'Sans Titre')
    body_en = ann.get('body', '')
    
    ann_lines = [
        "📢 <b>NOUVELLE ANNONCE OFFICIELLE CYBERLEEK</b>\n",
        f"🎯 <b>Titre :</b> <code>{title_en}</code>",
        f"📅 <b>Date :</b> {dt_str}\n",
        f"<blockquote>{body_en}</blockquote>"
    ]
    ann_text = "\n".join(ann_lines)
    
    print(f"\n[ANNONCE DÉTECTÉE] Publication de l'annonce '{title_en}'...", flush=True)
    screen_path = await asyncio.to_thread(capture_screenshot, "anns")
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

def get_paris_now():
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo("Europe/Paris"))
    except Exception:
        return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=2)))

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

def make_poll_bar(pct, length=20):
    filled = max(0, min(length, round(pct / (100 / length))))
    empty = length - filled
    return "█" * filled + "━" * empty

def format_polls_message():
    try:
        proc = subprocess.run(["node", os.path.join(SCRIPT_DIR, "get_poll_data.js")], capture_output=True, text=True, timeout=10)
        p = json.loads(proc.stdout.strip())
        now_str = get_paris_now().strftime("%H:%M:%S (Paris)")

        ends_at = p.get('ends_at')
        if ends_at:
            tz_fr = datetime.timezone(datetime.timedelta(hours=2))
            end_dt = datetime.datetime.fromtimestamp(ends_at, tz=tz_fr)
            end_str = end_dt.strftime("%d/%m/%Y à %H:%M")
        else:
            end_str = "Inconnue"

        poll_lines = [
            "📊 <b>TABLEAU DE BORD DES VOTES (MODE SILENCIEUX)</b>\n",
            f"🗳️ <b>Sujet :</b> {p['title']}",
            f"⏳ <b>Statut :</b> {p['status']}",
            f"📅 <b>Fin du vote :</b> {end_str} (dans {p['countdown']})\n"
        ]

        choices = p.get("choices", [])
        leader_choice = max(choices, key=lambda c: c.get("pct", 0)).get("choice") if choices else None

        fingerprint = []
        for c in choices:
            ch_name = c.get("choice", "")
            ch_pct = c.get("pct", 0.0)
            crown = "👑 " if ch_name == leader_choice else ""
            bar = make_poll_bar(ch_pct, length=20)
            poll_lines.append(f"{crown}<b>{ch_name}</b>")
            poll_lines.append(f"{bar} {ch_pct:.1f}%\n")
            fingerprint.append((ch_name, ch_pct))

        poll_lines.append(f"<i>🔄 Mis à jour en direct : {now_str}</i>")
        return "\n".join(poll_lines), (p['title'], p['status'], end_str, p['countdown'], tuple(fingerprint))

    except Exception as e:
        print(f"[Erreur format_polls_message] {e}", flush=True)
        return "", None

def format_leak_btn_label(lbl, url):
    lbl_lower = lbl.lower()
    if "arweave" in lbl_lower or "ar.io" in url or "arweave.net" in url:
        num = "".join(c for c in lbl_lower if c.isdigit())
        name = f"Arweave #{num}" if num else "Arweave"
    elif "bedrive" in lbl_lower or "bedrive.ru" in url:
        name = "Bedrive"
    elif "temp.sh" in lbl_lower or "temp.sh" in url:
        name = "Temp.sh"
    elif "upload.ee" in lbl_lower or "upload.ee" in url:
        name = "Upload.ee"
    elif "transfiles" in lbl_lower or "transfiles.ru" in url:
        name = "Transfiles"
    elif "gofile" in lbl_lower or "gofile.io" in url:
        name = "Gofile"
    elif "disroot" in lbl_lower or "disroot.org" in url:
        name = "Disroot"
    elif "lufi" in lbl_lower or "lufi.ethibox.fr" in url:
        name = "Lufi"
    else:
        name = lbl.split()[0]
    return f"📥 {name} 📥"

def format_leak_message_and_buttons(leak):
    tz_fr = datetime.timezone(datetime.timedelta(hours=2))
    dt_str = datetime.datetime.fromtimestamp(leak['timestamp'], tz=tz_fr).strftime("%d/%m/%Y à %H:%M")

    leak_lines = [
        "🚨 <b>NOUVEAU LEEK DÉTECTÉ</b> 🚨\n",
        f"🎯 <b>Nom du leak :</b> <code>{leak.get('title', 'Sans Titre')}</code>",
        f"📅 <b>Date :</b> {dt_str}\n",
        "👇 -------<b>TÉLÉCHARGEMENT DIRECT</b>-------👇"
    ]

    buttons = []
    items = leak.get("items", [])
    for it in items:
        lbl = it.get("label", "Télécharger").strip()
        url = it.get("url", "").strip()
        btn_txt = format_leak_btn_label(lbl, url)
        buttons.append(Button.url(btn_txt, url))

    keyboard_rows = []
    for i in range(0, len(buttons), 2):
        keyboard_rows.append(buttons[i:i+2])

    return "\n".join(leak_lines), (keyboard_rows if keyboard_rows else None)

def format_leak_message(leak):
    text, _ = format_leak_message_and_buttons(leak)
    return text

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
        html = resp.read().decode('utf-8', errors='replace')
        if "antibot" in html or "Button()" in html:
            inputs = dict(re.findall(r'name=\\?"([^\\"]+)\\?" type=\\?"hidden\\?" value=\\?"([^\\"]*)\\?"', html))
            img_match = re.search(r'data:image/png;base64,([A-Za-z0-9+/=]+)', html)
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
                if os.path.exists(dest) and os.path.getsize(dest) > 1024:
                    return True
        else:
            with open(dest, 'wb') as f_out:
                f_out.write(html.encode('utf-8'))
            if os.path.exists(dest) and os.path.getsize(dest) > 1024:
                return True
    except Exception as e:
        print(f"[Bedrive Downloader Notice] {e}", flush=True)
    return False

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
                if not saved_video:
                    saved_video = full_p
            elif f.lower().endswith(".zip"):
                if not saved_zip:
                    saved_zip = full_p

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
                    force_document=True,
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
        if any(gw in u_lower for gw in ["arweave.net", "vilenarios.com", "turbo-gateway.com", "ar.io", "permaweb.app"]):
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
                        downloaded_file = dest
                        file_size_mb = os.path.getsize(dest) / (1024 * 1024)
                        print(f"[Media Leak] Téléchargement Bedrive réussi ({file_size_mb:.2f} Mo) !", flush=True)
                        break

                # Essai téléchargement HTTP direct
                req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
                with urllib.request.urlopen(req, timeout=45) as resp, open(dest, 'wb') as f_out:
                    shutil.copyfileobj(resp, f_out)

                if os.path.exists(dest) and os.path.getsize(dest) > 1024:
                    with open(dest, 'rb') as f_chk:
                        prefix = f_chk.read(512).lower()
                        if b'<!doctype html' in prefix or b'<html' in prefix:
                            if b'download limit' in prefix or b'forbidden' in prefix or b'not found' in prefix:
                                os.remove(dest)
                                continue
                    downloaded_file = dest
                    file_size_mb = os.path.getsize(dest) / (1024 * 1024)
                    print(f"[Media Leak] Téléchargement réussi ({file_size_mb:.2f} Mo) !", flush=True)
                    break
            except Exception as e_dl:
                print(f"[Media Leak] Échec sur ce miroir ({u}) : {e_dl}", flush=True)

        if not downloaded_file:
            print("[Media Leak] Aucun fichier n'a pu être téléchargé depuis les miroirs.", flush=True)
            if auto_delete_delay:
                err_msg = await client.send_message(
                    channel,
                    message="⚠️ <i>Le fichier original de ce leak n'a pas pu être téléchargé automatiquement (les liens temporaires externes ont expiré ou sont hors-ligne). Veuillez utiliser les liens directs de téléchargement ci-dessus.</i>",
                    parse_mode='html',
                    reply_to=reply_to_id
                )
                asyncio.create_task(delete_after_delay(client, channel, err_msg.id, auto_delete_delay))
            return

        is_zip = False
        try:
            with open(downloaded_file, 'rb') as f_check:
                header = f_check.read(4)
                if header.startswith(b'PK\x03\x04'):
                    is_zip = True
        except Exception:
            pass

        if is_zip or downloaded_file.lower().endswith('.zip'):
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
                    if any(f.lower().endswith(ext) for ext in [".mp4", ".mkv", ".mov", ".webm", ".avi", ".png", ".jpg"]):
                        media_extracted = os.path.join(root, f)
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
                    force_document=True,
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

        else:
            raw_size_mb = os.path.getsize(downloaded_file) / (1024 * 1024)
            file_cap = (
                f"🎬 <b>Fichier original du leak</b> : <code>{title}</code>\n"
                f"📁 <i>Fichier : {os.path.basename(downloaded_file)} ({raw_size_mb:.2f} Mo)</i>\n"
                f"✨ <i>Qualité 100% brute d'origine (sans compression)</i>"
            )
            print(f"[Media Leak] Envoi du fichier brut sur Telegram...", flush=True)
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

    session = StringSession(SESSION_STRING) if SESSION_STRING else StringSession()
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
                BotCommand(command='hub', description="Ouvrir la Mini App privée GTA 6 Vault"),
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
        raw = (event.raw_text or event.text or "").strip()
        if not raw.startswith('/'):
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
            if cmd in ['/hub', '/app', '/vault']:
                hub_url = "https://cyberleek-alerter.onrender.com"
                hub_text = (
                    "🕹️ <b>CYBERLEEK GTA 6 VAULT // MINI APP</b>\n\n"
                    "Accédez à l'application web privée inspirée de l'interface Cyberleek :\n"
                    "  • 🔍 Recherche instantanée par nom ou vidéo\n"
                    "  • 🔑 Copie en 1-clic des mots de passe d'archives\n"
                    "  • ⚡ Accès direct aux 21 leaks et miroirs rapides\n"
                    "  • 📊 Stats $CYBERLEEK, sondage et statut des miroirs en direct\n\n"
                    "Cliquez sur le bouton ci-dessous pour lancer le Vault :"
                )
                hub_btn = [
                    [Button.url("🚀 Ouvrir le Vault GTA 6 🚀", hub_url)]
                ]
                await reply_and_auto_delete(hub_text, buttons=hub_btn, delay=60)

            elif cmd in ['/start', '/help']:
                help_text = (
                    "🤖 <b>CYBERLEEK ALERTER BOT</b> 🤖\n\n"
                    "Surveillance autonome 24h/24 du site Cyberleek et de la blockchain Solana.\n\n"
                    "📌 <b>Commandes disponibles :</b>\n"
                    "  • 🚀 /hub - Ouvrir la Mini App privée GTA 6 Vault (Recherche & Miroirs)\n"
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
                await reply_and_auto_delete(m_text)

            elif cmd in ['/announcements', '/anns', '/news']:
                anns = fetch_announcements()
                if anns:
                    anns.sort(key=lambda x: x.get('timestamp', 0))
                    last_a = anns[-1]
                    tz_fr = datetime.timezone(datetime.timedelta(hours=2))
                    dt_str = datetime.datetime.fromtimestamp(last_a['timestamp'], tz=tz_fr).strftime("%d/%m/%Y à %H:%M (Paris)")
                    t_en = last_a.get('title', 'Sans Titre')
                    b_en = last_a.get('body', '')
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

            # 3. MODIFICATION DYNAMIQUE DE LA CRYPTO ET PALIERS MCAP (toutes les 20s)
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

                # Vérification de renversement de leader dans le vote
                try:
                    proc_poll = subprocess.run(["node", os.path.join(SCRIPT_DIR, "get_poll_data.js")], capture_output=True, text=True, timeout=10)
                    poll_res = json.loads(proc_poll.stdout.strip())
                    p_choices = poll_res.get("choices", [])
                    if p_choices:
                        leader_obj = max(p_choices, key=lambda c: c.get("pct", 0))
                        current_lead = leader_obj.get("choice")
                        last_lead = seen.get("last_poll_leader")
                        if last_lead and current_lead != last_lead:
                            flip_lines = [
                                "🗳️ <b>CHANGEMENT DE LEADER DANS LE VOTE GTA 6 !</b> 🗳️\n",
                                f"🔥 <b>{current_lead}</b> vient de devancer <b>{last_lead}</b> !\n",
                                "📊 <b>Nouveaux résultats :</b>\n"
                            ]
                            for c in p_choices:
                                ch_name = c.get("choice", "")
                                ch_pct = c.get("pct", 0.0)
                                crown = "👑 " if ch_name == current_lead else ""
                                bar = make_poll_bar(ch_pct, length=20)
                                flip_lines.append(f"{crown}<b>{ch_name}</b>")
                                flip_lines.append(f"{bar} {ch_pct:.1f}%\n")
                            flip_text = "\n".join(flip_lines)
                            sent_flip = await client.send_message(channel, message=flip_text, parse_mode='html')
                            asyncio.create_task(delete_after_delay(client, channel, sent_flip.id, 180))
                            seen["last_poll_leader"] = current_lead
                            save_seen(seen)
                        elif not last_lead:
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
                    if mirrors_fp != last_mirrors_fp:
                        try:
                            await client.edit_message(channel, message=mirrors_id, text=mirrors_text, parse_mode='html')
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

