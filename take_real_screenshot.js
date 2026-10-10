const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');

const CHROME_PATH = process.env.CHROME_BIN || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/usr/bin/chromium');
const PORT = 9222;
const TARGET_URL = 'https://cyberleek.saiph.weavegate.net/';
const OUT_PATH = path.join(__dirname, 'real_live_website_screenshot.png');

async function main() {
  const chromeProc = spawn(CHROME_PATH, [
    `--remote-debugging-port=${PORT}`,
    '--headless=new',
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-dev-shm-usage',
    '--disable-gpu',
    '--single-process',
    '--hide-scrollbars',
    '--window-size=1280,900',
    '--ignore-certificate-errors',
    '--user-data-dir=' + path.join(__dirname, 'chrome_temp_profile')
  ]);

  let wsUrl = null;
  for (let i = 0; i < 30; i++) {
    await new Promise(r => setTimeout(r, 200));
    try {
      const res = await new Promise((resolve, reject) => {
        http.get(`http://127.0.0.1:${PORT}/json/version`, resp => {
          let data = '';
          resp.on('data', chunk => data += chunk);
          resp.on('end', () => resolve(JSON.parse(data)));
        }).on('error', reject);
      });
      if (res && res.webSocketDebuggerUrl) {
        wsUrl = res.webSocketDebuggerUrl;
        break;
      }
    } catch (e) {}
  }

  if (!wsUrl) {
    chromeProc.kill();
    return;
  }

  const ws = new WebSocket(wsUrl);
  let id = 1;
  const callbacks = new Map();
  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && callbacks.has(msg.id)) {
      callbacks.get(msg.id)(msg);
      callbacks.delete(msg.id);
    }
  };

  function send(method, params = {}) {
    return new Promise(resolve => {
      const reqId = id++;
      callbacks.set(reqId, resolve);
      ws.send(JSON.stringify({ id: reqId, method, params }));
    });
  }
  await new Promise(r => ws.onopen = r);

  const targetRes = await send('Target.createTarget', { url: TARGET_URL });
  const targetId = targetRes.result.targetId;
  const pageWsUrl = `ws://127.0.0.1:${PORT}/devtools/page/${targetId}`;

  const pageWs = new WebSocket(pageWsUrl);
  let pageId = 1;
  const pageCallbacks = new Map();
  pageWs.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pageCallbacks.has(msg.id)) {
      pageCallbacks.get(msg.id)(msg);
      pageCallbacks.delete(msg.id);
    }
  };
  function pageSend(method, params = {}) {
    return new Promise(resolve => {
      const reqId = pageId++;
      pageCallbacks.set(reqId, resolve);
      pageWs.send(JSON.stringify({ id: reqId, method, params }));
    });
  }
  await new Promise(r => pageWs.onopen = r);

  await pageSend('Runtime.enable');
  await pageSend('Page.enable');
  await pageSend('Page.navigate', { url: TARGET_URL });

  // Attendre le chargement naturel des leaks réels
  for (let i = 0; i < 40; i++) {
    await new Promise(r => setTimeout(r, 500));
    const evalRes = await pageSend('Runtime.evaluate', {
      expression: `(() => {
        const c = document.getElementById('content');
        return c && c.querySelectorAll('.content-item').length > 0;
      })()`,
      returnByValue: true
    });
    if (evalRes.result?.result?.value) break;
  }

  // Défilement 100% naturel sur les leaks (comme l'utilisateur avec sa molette)
  // AUCUNE MODIFICATION DU DOM, AUCUNE SUPPRESSION, RIEN DE TOUCHÉ !
  await pageSend('Runtime.evaluate', {
    expression: `(() => {
      const card = document.getElementById('card-content');
      if (card) {
        card.scrollIntoView({ behavior: 'instant', block: 'start' });
      }
    })()`
  });

  await new Promise(r => setTimeout(r, 600));

  // Capture brute sans retouche
  const screenshotRes = await pageSend('Page.captureScreenshot', {
    format: 'png'
  });

  if (screenshotRes.result && screenshotRes.result.data) {
    const buf = Buffer.from(screenshotRes.result.data, 'base64');
    fs.writeFileSync(OUT_PATH, buf);
    console.log(`✅ Capture 100% brute du site enregistrée (${buf.length} bytes)`);
  }

  pageWs.close();
  ws.close();
  chromeProc.kill();
  process.exit(0);
}

main().catch(console.error);
