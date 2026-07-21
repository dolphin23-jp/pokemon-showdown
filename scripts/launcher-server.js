'use strict';

const crypto = require('crypto');
const fs = require('fs');
const http = require('http');
const https = require('https');
const net = require('net');
const path = require('path');

const LISTEN_PORT = Number.parseInt(process.env.LAUNCHER_PORT || process.env.PORT || '3000', 10);
const SHOWDOWN_PORT = Number.parseInt(process.env.SHOWDOWN_PORT || '8000', 10);
const BOT_USERNAME = process.env.BOT_USERNAME || 'FoulPlayBot';
const BOT_FORMAT = process.env.BOT_FORMAT || 'gen9nationaldexallgenerationsbss';
const BOT_FORMAT_LABEL = process.env.BOT_FORMAT_LABEL || BOT_FORMAT;
const TEAM_LIBRARY_DIR = process.env.TEAM_LIBRARY_DIR || '';
const TEAM_METADATA = process.env.TEAM_METADATA || '';
const DEFAULT_PLAYER_NAME = process.env.DEFAULT_PLAYER_NAME || 'Dolphin23';
const ACCESS_TOKEN = process.env.ACCESS_TOKEN || '';
const OFFICIAL_CLIENT_HOST = 'play.pokemonshowdown.com';
const ACCESS_COOKIE = 'showdown_ai_access';
const ACCESS_DIGEST = ACCESS_TOKEN ? crypto.createHash('sha256').update(ACCESS_TOKEN).digest('hex') : '';

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function send(res, statusCode, contentType, body, extraHeaders = {}) {
  const payload = Buffer.from(body);
  res.writeHead(statusCode, {
    'content-type': contentType,
    'content-length': payload.length,
    'cache-control': 'no-store',
    ...extraHeaders,
  });
  res.end(payload);
}

function redirect(res, location, extraHeaders = {}) {
  res.writeHead(303, { location, 'cache-control': 'no-store', ...extraHeaders });
  res.end();
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
    input[type=text], input[type=password] { box-sizing: border-box; width: min(100%, 360px); padding: 10px 12px; font: inherit; border: 1px solid #8c959f88; border-radius: 8px; }
    .meta { margin-top: -6px; font-size: 0.92rem; color: #656d76; }
    .error { color: #cf222e; font-weight: 700; }
    h1, h2 { line-height: 1.25; }
  </style>`;
}

function parseCookies(req) {
  const cookies = {};
  for (const pair of String(req.headers.cookie || '').split(';')) {
    const index = pair.indexOf('=');
    if (index < 0) continue;
    cookies[pair.slice(0, index).trim()] = decodeURIComponent(pair.slice(index + 1).trim());
  }
  return cookies;
}

function constantTimeEqual(left, right) {
  const a = Buffer.from(String(left));
  const b = Buffer.from(String(right));
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

function hasAccess(req) {
  if (!ACCESS_TOKEN) return true;
  return constantTimeEqual(parseCookies(req)[ACCESS_COOKIE] || '', ACCESS_DIGEST);
}

function accessCookie() {
  return `${ACCESS_COOKIE}=${encodeURIComponent(ACCESS_DIGEST)}; Path=/; Max-Age=31536000; HttpOnly; Secure; SameSite=Lax`;
}

function accessHtml(message = '') {
  return `<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Pokemon Showdown AI - Access</title>
  ${commonStyles()}
</head>
<body>
  <h1>Pokemon Showdown AI</h1>
  <div class="card">
    <p>このサーバーは個人用です。Render作成時に設定したアクセスキーを入力してください。</p>
    ${message ? `<p class="error">${escapeHtml(message)}</p>` : ''}
    <form method="post" action="/access">
      <p><input type="password" name="key" autocomplete="current-password" required autofocus></p>
      <button class="button" type="submit">開く</button>
    </form>
  </div>
</body>
</html>`;
}

function readTeamMetadata() {
  if (!TEAM_METADATA || !fs.existsSync(TEAM_METADATA)) return [];
  const rows = [];
  for (const line of fs.readFileSync(TEAM_METADATA, 'utf8').split(/\r?\n/)) {
    if (!line.trim() || line.trimStart().startsWith('#')) continue;
    const [id, slug, title, author, source] = line.split('\t');
    if (!id || !slug) continue;
    const file = TEAM_LIBRARY_DIR ? path.join(TEAM_LIBRARY_DIR, `${slug}.txt`) : '';
    rows.push({
      id,
      slug,
      title: title || slug,
      author: author || 'Unknown',
      source: source || '',
      team: file && fs.existsSync(file) ? fs.readFileSync(file, 'utf8').trim() : '',
    });
  }
  return rows;
}

function formatInfo() {
  if (BOT_FORMAT === 'gen9nationaldexallgenerationsbss') {
    return {
      title: '[Gen 9] National Dex All Generations BSS',
      summary: '全世代の公式ポケモン・技・持ち物・特性を、第9世代の対戦仕様で使用します。禁止級・幻・同種・持ち物重複の制限はなく、6体を見せて3体を選出、レベル50に統一します。',
      hasLibrary: true,
    };
  }
  if (BOT_FORMAT === 'gen9bssregi') {
    return {
      title: '[Gen 9] BSS Reg I',
      summary: 'スカーレット・バイオレットのRegulation Iに準拠した、6体見せ合い・3体選出のルールです。',
      hasLibrary: true,
    };
  }
  return {
    title: '[Gen 9] Random Battle',
    summary: 'チームを自動生成して6対6で戦うランダムバトルです。',
    hasLibrary: false,
  };
}

function playerNameScript() {
  return `<script>
    const fallbackPlayerName = ${JSON.stringify(DEFAULT_PLAYER_NAME)};
    const input = document.getElementById('player-name');
    if (input) input.value = localStorage.getItem('showdown-player-name') || fallbackPlayerName;
    document.getElementById('open-client-form')?.addEventListener('submit', event => {
      event.preventDefault();
      const cleaned = String(input?.value || '').replace(/[|,;]+/g, '').trim();
      if (!/[A-Za-z]/.test(cleaned)) {
        alert('名前には英字を1文字以上含めてください。');
        return;
      }
      localStorage.setItem('showdown-player-name', cleaned.slice(0, 18));
      location.href = '/client.html';
    });
  </script>`;
}

function launcherHtml() {
  const username = escapeHtml(BOT_USERNAME);
  const format = formatInfo();
  const teams = readTeamMetadata().filter(team => team.team);
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
       <strong>対戦形式:</strong> <code>${escapeHtml(format.title)}</code>${format.hasLibrary ? `<br><strong>Bot構築:</strong> 対戦ごとに${teams.length}構築からランダム選択` : ''}</p>
    <p>${escapeHtml(format.summary)}</p>
    <form id="open-client-form">
      <p><label><strong>あなたの名前</strong><br><input id="player-name" type="text" maxlength="18" autocomplete="nickname"></label></p>
      <button class="button" type="submit">名前を保存してShowdownを開く</button>
      ${format.hasLibrary ? '<a class="button secondary" href="/teams.html">構築ライブラリを開く</a>' : ''}
    </form>
    ${format.hasLibrary ? `
    <ol>
      <li>構築ライブラリから好きな構築をコピーします。</li>
      <li>ShowdownのTeambuilderで <code>${escapeHtml(format.title)}</code> の新規チームを作り、Import/Exportへ貼り付けます。</li>
      <li><code>${username}</code> を検索し、同じ形式で対戦を申し込みます。</li>
      <li>6体見せ合い後に3体を選出します。Botも自動で3体を選びます。</li>
    </ol>` : `
    <ol>
      <li><code>${username}</code> を検索します。</li>
      <li><code>${escapeHtml(BOT_FORMAT_LABEL)}</code> で対戦を申し込みます。</li>
      <li>Botが自動で受諾します。</li>
    </ol>`}
    <p class="note">名前はこのブラウザに保存され、次回から自動設定されます。CodespaceのコンソールへIDを入力する必要はありません。</p>
  </div>
  ${playerNameScript()}
</body>
</html>`;
}

function teamsHtml() {
  const teams = readTeamMetadata();
  const format = formatInfo();
  const cards = teams.map((team, index) => {
    const body = team.team ? escapeHtml(team.team) : '構築を取得できませんでした。管理画面からチームライブラリを更新してください。';
    const sourceLink = /^\d+$/.test(team.id) ?
      ` · <a href="https://teams.pokemonshowdown.com/view/${encodeURIComponent(team.id)}" target="_blank" rel="noopener">原典を開く</a>` : '';
    return `<section class="card">
      <h2>${index + 1}. ${escapeHtml(team.title)}</h2>
      <p class="meta">作成者: ${escapeHtml(team.author)}${team.source ? ` · ${escapeHtml(team.source)}` : ''}${sourceLink}</p>
      <button class="button copy" data-target="team-${index}" ${team.team ? '' : 'disabled'}>構築をコピー</button>
      <textarea id="team-${index}" readonly>${body}</textarea>
    </section>`;
  }).join('\n');

  return `<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${escapeHtml(BOT_FORMAT_LABEL)} 構築ライブラリ</title>
  ${commonStyles()}
</head>
<body>
  <p><a href="/">← 入口へ戻る</a></p>
  <h1>${escapeHtml(BOT_FORMAT_LABEL)} 構築ライブラリ</h1>
  <div class="card">
    <p>現在${teams.filter(team => team.team).length}件の構築を利用できます。Botもこのライブラリから毎試合ランダムに選びます。</p>
    <p><strong>使い方:</strong> 「構築をコピー」→ Showdownの <strong>Teambuilder</strong> → <strong>New Team</strong> → <strong>${escapeHtml(format.title)}</strong> → <strong>Import/Export</strong> → 貼り付け。</p>
    <button id="random-copy" class="button">ランダムな構築を1つコピー</button>
    <a class="button secondary" href="/">名前を設定してShowdownを開く</a>
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
Config.defaultserver = {
  id: 'personalai',
  protocol: location.protocol.replace(':', ''),
  host: location.hostname,
  port: Number(location.port || (location.protocol === 'https:' ? 443 : 80)),
  httpport: Number(location.port || (location.protocol === 'https:' ? 443 : 80)),
  altport: Number(location.port || (location.protocol === 'https:' ? 443 : 80)),
  prefix: '/showdown',
  registered: false
};
Config.server = Config.defaultserver;

(() => {
  const defaultPlayerName = ${JSON.stringify(DEFAULT_PLAYER_NAME)};
  let attempts = 0;
  const timer = setInterval(() => {
    attempts++;
    const ps = globalThis.PS;
    if (ps?.user && !ps.user.__personalServerLoginPatched) {
      ps.user.__personalServerLoginPatched = true;
      ps.user.changeName = function (name) {
        const cleaned = String(name || '').replace(/[|,;]+/g, '').trim().slice(0, 18);
        if (!/[A-Za-z]/.test(cleaned)) {
          this.updateLogin?.({ name: cleaned, error: 'Usernames must contain at least one letter.' });
          return;
        }
        localStorage.setItem('showdown-player-name', cleaned);
        this.loggingIn = null;
        ps.send('/trn ' + cleaned + ',0,');
        this.update?.({ success: true });
      };
    }
    const savedName = localStorage.getItem('showdown-player-name') || defaultPlayerName;
    if (ps?.user && savedName && !ps.user.named && ps.user.challstr && !ps.user.__personalServerAutoLoginSent) {
      ps.user.__personalServerAutoLoginSent = true;
      ps.user.changeName(savedName);
    }
    if (ps?.user?.named && ps.user.__personalServerLoginPatched && !ps.user.__personalServerJapaneseLanguageSent) {
      ps.user.__personalServerJapaneseLanguageSent = true;
      ps.send('/updatesettings ' + JSON.stringify({ language: 'japanese' }));
    }
    if ((ps?.user?.named && ps.user.__personalServerLoginPatched && ps.user.__personalServerJapaneseLanguageSent) || attempts > 400) {
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
      'user-agent': 'Pokemon-Showdown-Personal-AI-Proxy',
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
      send(res, 200, 'text/html; charset=utf-8', html.replace(marker, `${clientConfigInjection()}\n\t${marker}`));
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
    delete responseHeaders['set-cookie'];
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

function handleAccess(req, res) {
  let body = '';
  req.setEncoding('utf8');
  req.on('data', chunk => {
    body += chunk;
    if (body.length > 8192) req.destroy();
  });
  req.on('end', () => {
    const supplied = new URLSearchParams(body).get('key') || '';
    if (ACCESS_TOKEN && constantTimeEqual(supplied, ACCESS_TOKEN)) {
      redirect(res, '/', { 'set-cookie': accessCookie() });
    } else {
      send(res, 401, 'text/html; charset=utf-8', accessHtml('アクセスキーが違います。'));
    }
  });
}

const server = http.createServer((req, res) => {
  const pathname = new URL(req.url, 'http://localhost').pathname;

  if (pathname === '/health') {
    send(res, 200, 'application/json; charset=utf-8', JSON.stringify({ ok: true, format: BOT_FORMAT }));
    return;
  }
  if (pathname === '/access' && req.method === 'POST') {
    handleAccess(req, res);
    return;
  }
  if (!hasAccess(req)) {
    send(res, 401, 'text/html; charset=utf-8', accessHtml());
    return;
  }
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
  if (!hasAccess(req) || !pathname.startsWith('/showdown')) {
    clientSocket.end('HTTP/1.1 401 Unauthorized\r\nConnection: close\r\n\r\n');
    return;
  }

  const upstreamSocket = net.connect(SHOWDOWN_PORT, '127.0.0.1');
  upstreamSocket.setNoDelay(true);
  clientSocket.setNoDelay(true);

  upstreamSocket.on('connect', () => {
    const headers = { ...req.headers, host: `127.0.0.1:${SHOWDOWN_PORT}` };
    delete headers.cookie;
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
