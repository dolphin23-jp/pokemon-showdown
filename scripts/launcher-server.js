'use strict';

const fs = require('fs');
const http = require('http');
const https = require('https');
const net = require('net');
const path = require('path');

const LISTEN_PORT = Number.parseInt(process.env.LAUNCHER_PORT || '3000', 10);
const SHOWDOWN_PORT = Number.parseInt(process.env.SHOWDOWN_PORT || '8000', 10);
const BOT_USERNAME = process.env.BOT_USERNAME || 'FoulPlayBot';
const BOT_FORMAT = process.env.BOT_FORMAT || 'gen9bssregi';
const TEAM_LIBRARY_DIR = process.env.TEAM_LIBRARY_DIR || '';
const TEAM_MANIFEST = process.env.TEAM_MANIFEST || '';
const OFFICIAL_CLIENT_HOST = 'play.pokemonshowdown.com';

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function send(res, statusCode, contentType, body) {
  const payload = Buffer.from(body);
  res.writeHead(statusCode, {
    'content-type': contentType,
    'content-length': payload.length,
    'cache-control': 'no-store',
  });
  res.end(payload);
}

function commonStyles() {
  return `<style>
    :root { color-scheme: light dark; }
    body { font-family: system-ui, sans-serif; max-width: 900px; margin: 0 auto; padding: 28px 18px 60px; line-height: 1.65; }
    .card { border: 1px solid #8c959f66; border-radius: 14px; padding: 20px; margin: 16px 0; }
    .button { display: inline-block; padding: 11px 16px; margin: 4px 6px 4px 0; border: 0; border-radius: 10px; background: #0969da; color: white; text-decoration: none; font-weight: 700; cursor: pointer; }
    .button.secondary { background: #57606a; }
    code { background: #8c959f22; padding: 2px 6px; border-radius: 6px; word-break: break-all; }
    .note { color: #656d76; }
    textarea { box-sizing: border-box; width: 100%; min-height: 290px; padding: 12px; font: 13px/1.45 ui-monospace, SFMono-Regular, Menlo, monospace; border: 1px solid #8c959f66; border-radius: 10px; }
    .meta { margin-top: -6px; font-size: 0.92rem; color: #656d76; }
    h1, h2 { line-height: 1.25; }
  </style>`;
}

function readTeamManifest() {
  if (!TEAM_MANIFEST || !fs.existsSync(TEAM_MANIFEST)) return [];
  const rows = [];
  for (const line of fs.readFileSync(TEAM_MANIFEST, 'utf8').split(/\r?\n/)) {
    if (!line.trim() || line.trimStart().startsWith('#')) continue;
    const [id, slug, title, author] = line.split('\t');
    if (!id || !slug) continue;
    const file = TEAM_LIBRARY_DIR ? path.join(TEAM_LIBRARY_DIR, `${slug}.txt`) : '';
    rows.push({
      id,
      slug,
      title: title || slug,
      author: author || 'Unknown',
      team: file && fs.existsSync(file) ? fs.readFileSync(file, 'utf8').trim() : '',
    });
  }
  return rows;
}

function launcherHtml() {
  const username = escapeHtml(BOT_USERNAME);
  const format = escapeHtml(BOT_FORMAT);
  const isBss = BOT_FORMAT === 'gen9bssregi';
  const teamCount = readTeamManifest().filter(team => team.team).length;
  return `<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Pokemon Showdown AI</title>
  ${commonStyles()}
</head>
<body>
  <h1>Pokemon Showdown AI</h1>
  <div class="card">
    <p>Showdownサーバーとfoul-play Botは起動済みです。</p>
    <p><strong>Bot名:</strong> <code>${username}</code><br>
       <strong>対戦形式:</strong> <code>${format}</code>${isBss ? '<br><strong>Bot構築:</strong> 対戦ごとに' + teamCount + '構築からランダム選択' : ''}</p>
    <p>
      <a class="button" href="/client.html">Showdownを開く</a>
      ${isBss ? '<a class="button secondary" href="/teams.html">構築ライブラリを開く</a>' : ''}
    </p>
    ${isBss ? `
    <ol>
      <li>構築ライブラリから好きな構築をコピーします。</li>
      <li>ShowdownのTeambuilderで <code>[Gen 9] BSS Reg I</code> の新規チームを作り、Import/Exportへ貼り付けます。</li>
      <li><code>${username}</code> を検索し、<code>gen9bssregi</code> で対戦を申し込みます。</li>
      <li>6体見せ合い後に3体を選出します。Botも自動で3体を選びます。</li>
    </ol>` : `
    <ol>
      <li>Showdownで自分の名前を設定します。</li>
      <li><code>${username}</code> を検索して、<code>${format}</code> で対戦を申し込みます。</li>
      <li>Botが自動で受諾します。</li>
    </ol>`}
    <p class="note">モード変更: Codespaceのターミナルで <code>bash scripts/showdown-ai.sh mode bss</code> または <code>bash scripts/showdown-ai.sh mode random</code></p>
  </div>
</body>
</html>`;
}

function teamsHtml() {
  const teams = readTeamManifest();
  const cards = teams.map((team, index) => {
    const body = team.team ? escapeHtml(team.team) : '構築を取得できませんでした。Codespaceで refresh-teams を実行してください。';
    return `<section class="card">
      <h2>${index + 1}. ${escapeHtml(team.title)}</h2>
      <p class="meta">作成者: ${escapeHtml(team.author)} · <a href="https://teams.pokemonshowdown.com/view/${encodeURIComponent(team.id)}" target="_blank" rel="noopener">原典を開く</a></p>
      <button class="button copy" data-target="team-${index}" ${team.team ? '' : 'disabled'}>構築をコピー</button>
      <textarea id="team-${index}" readonly>${body}</textarea>
    </section>`;
  }).join('\n');

  return `<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>BSS Reg I 構築ライブラリ</title>
  ${commonStyles()}
</head>
<body>
  <p><a href="/">← 入口へ戻る</a></p>
  <h1>BSS Reg I 構築ライブラリ</h1>
  <div class="card">
    <p>Smogonの公式BSS Sample Teamsに掲載されたRegulation I構築です。現在${teams.filter(team => team.team).length}件あります。</p>
    <p><strong>使い方:</strong> 「構築をコピー」→ Showdownの <strong>Teambuilder</strong> → <strong>New Team</strong> → <strong>[Gen 9] BSS Reg I</strong> → <strong>Import/Export</strong> → 貼り付け。</p>
    <button id="random-copy" class="button">ランダムな構築を1つコピー</button>
    <a class="button secondary" href="/client.html">Showdownを開く</a>
  </div>
  ${cards || '<p>構築ライブラリがまだ準備されていません。</p>'}
  <script>
    async function copyText(textarea, button) {
      try {
        await navigator.clipboard.writeText(textarea.value);
      } catch (_error) {
        textarea.focus();
        textarea.select();
        document.execCommand('copy');
      }
      const old = button.textContent;
      button.textContent = 'コピーしました';
      setTimeout(() => { button.textContent = old; }, 1800);
    }
    document.querySelectorAll('button.copy').forEach(button => {
      button.addEventListener('click', () => {
        const textarea = document.getElementById(button.dataset.target);
        if (textarea && textarea.value) copyText(textarea, button);
      });
    });
    document.getElementById('random-copy')?.addEventListener('click', event => {
      const choices = [...document.querySelectorAll('textarea')].filter(x => x.value && !x.value.startsWith('構築を取得'));
      if (!choices.length) return;
      copyText(choices[Math.floor(Math.random() * choices.length)], event.currentTarget);
    });
  </script>
</body>
</html>`;
}

function clientConfigInjection() {
  return `<script>
// Codespaces: use the authenticated 3000-port origin for both the client and WebSocket proxy.
Config.defaultserver = {
  id: 'codespace',
  protocol: 'https',
  host: location.hostname,
  port: 443,
  httpport: 443,
  altport: 443,
  prefix: '/showdown',
  registered: false
};
Config.server = Config.defaultserver;

// Local servers with noguestsecurity do not need the public login server.
// Patch Choose name once the client model is available so iPad users can name themselves normally.
(() => {
  let attempts = 0;
  const timer = setInterval(() => {
    attempts++;
    const ps = globalThis.PS;
    if (ps?.user && !ps.user.__codespacesLocalLogin) {
      ps.user.__codespacesLocalLogin = true;
      ps.user.changeName = function (name) {
        const cleaned = String(name || '').replace(/[|,;]+/g, '').trim();
        if (!/[A-Za-z]/.test(cleaned)) {
          this.updateLogin?.({ name: cleaned, error: 'Usernames must contain at least one letter.' });
          return;
        }
        this.loggingIn = null;
        ps.send('/trn ' + cleaned + ',0,');
        this.update?.({ success: true });
      };
      clearInterval(timer);
    } else if (attempts > 200) {
      clearInterval(timer);
    }
  }, 50);
})();
</script>`;
}

function servePatchedClient(res) {
  const request = https.get({
    hostname: OFFICIAL_CLIENT_HOST,
    path: '/testclient-new.html',
    headers: {
      accept: 'text/html',
      'user-agent': 'Pokemon-Showdown-Codespaces-Proxy',
    },
  }, upstream => {
    const chunks = [];
    upstream.on('data', chunk => chunks.push(chunk));
    upstream.on('end', () => {
      if (upstream.statusCode !== 200) {
        send(res, 502, 'text/plain; charset=utf-8', `Official client returned HTTP ${upstream.statusCode || 'unknown'}.`);
        return;
      }

      const html = Buffer.concat(chunks).toString('utf8');
      const marker = '<script nomodule src="/js/lib/ps-polyfill.js"></script>';
      if (!html.includes(marker)) {
        send(res, 502, 'text/plain; charset=utf-8', 'Could not patch the current Pokemon Showdown test client.');
        return;
      }

      const patched = html.replace(marker, `${clientConfigInjection()}\n\t${marker}`);
      send(res, 200, 'text/html; charset=utf-8', patched);
    });
  });

  request.on('error', error => {
    send(res, 502, 'text/plain; charset=utf-8', `Could not load the official Pokemon Showdown client: ${error.message}`);
  });
  request.setTimeout(30000, () => request.destroy(new Error('request timed out')));
}

function proxyRequest(req, res, target) {
  const isShowdown = target === 'showdown';
  const transport = isShowdown ? http : https;
  const headers = { ...req.headers };
  delete headers.cookie;
  delete headers.authorization;
  delete headers['proxy-authorization'];
  headers.host = isShowdown ? `127.0.0.1:${SHOWDOWN_PORT}` : OFFICIAL_CLIENT_HOST;

  const upstream = transport.request({
    hostname: isShowdown ? '127.0.0.1' : OFFICIAL_CLIENT_HOST,
    port: isShowdown ? SHOWDOWN_PORT : 443,
    method: req.method,
    path: req.url,
    headers,
  }, upstreamResponse => {
    const responseHeaders = { ...upstreamResponse.headers };
    if (responseHeaders.location && !isShowdown) {
      responseHeaders.location = responseHeaders.location.replace(`https://${OFFICIAL_CLIENT_HOST}`, '');
    }
    res.writeHead(upstreamResponse.statusCode || 502, responseHeaders);
    upstreamResponse.pipe(res);
  });

  upstream.on('error', error => {
    if (!res.headersSent) {
      send(res, 502, 'text/plain; charset=utf-8', `Proxy error: ${error.message}`);
    } else {
      res.destroy(error);
    }
  });
  upstream.setTimeout(60000, () => upstream.destroy(new Error('proxy request timed out')));
  req.pipe(upstream);
}

function serializeHeaders(headers) {
  const lines = [];
  for (const [name, value] of Object.entries(headers)) {
    if (Array.isArray(value)) {
      for (const item of value) lines.push(`${name}: ${item}`);
    } else if (value !== undefined) {
      lines.push(`${name}: ${value}`);
    }
  }
  return lines;
}

const server = http.createServer((req, res) => {
  const pathname = new URL(req.url, 'http://localhost').pathname;

  if (pathname === '/') {
    send(res, 200, 'text/html; charset=utf-8', launcherHtml());
    return;
  }
  if (pathname === '/teams.html') {
    send(res, 200, 'text/html; charset=utf-8', teamsHtml());
    return;
  }
  if (pathname === '/client.html') {
    servePatchedClient(res);
    return;
  }
  if (pathname === '/health') {
    send(res, 200, 'application/json; charset=utf-8', JSON.stringify({ ok: true, format: BOT_FORMAT }));
    return;
  }
  if (pathname === '/favicon.ico') {
    res.writeHead(302, { location: '/favicon-256.png' });
    res.end();
    return;
  }
  if (pathname.startsWith('/showdown')) {
    proxyRequest(req, res, 'showdown');
    return;
  }

  proxyRequest(req, res, 'official-client');
});

server.on('upgrade', (req, clientSocket, head) => {
  const pathname = new URL(req.url, 'http://localhost').pathname;
  if (!pathname.startsWith('/showdown')) {
    clientSocket.destroy();
    return;
  }

  const upstreamSocket = net.connect(SHOWDOWN_PORT, '127.0.0.1');
  upstreamSocket.setNoDelay(true);
  clientSocket.setNoDelay(true);

  upstreamSocket.on('connect', () => {
    const headers = { ...req.headers, host: `127.0.0.1:${SHOWDOWN_PORT}` };
    const requestHead = [
      `${req.method} ${req.url} HTTP/${req.httpVersion}`,
      ...serializeHeaders(headers),
      '',
      '',
    ].join('\r\n');
    upstreamSocket.write(requestHead);
    if (head.length) upstreamSocket.write(head);
    clientSocket.pipe(upstreamSocket).pipe(clientSocket);
  });

  const closeBoth = error => {
    if (error) console.error('WebSocket proxy error:', error.message);
    clientSocket.destroy();
    upstreamSocket.destroy();
  };
  upstreamSocket.on('error', closeBoth);
  clientSocket.on('error', closeBoth);
});

server.on('clientError', (_error, socket) => {
  socket.end('HTTP/1.1 400 Bad Request\r\n\r\n');
});

server.listen(LISTEN_PORT, '0.0.0.0', () => {
  console.log(`Launcher and Showdown client proxy listening on port ${LISTEN_PORT}.`);
});
