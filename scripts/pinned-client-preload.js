'use strict';

const crypto = require('crypto');
const fs = require('fs');
const http = require('http');
const path = require('path');

const LOCAL_CLIENT_PREFIX = '/local-client/';
const LOCAL_CLIENT_ENTRY = `${LOCAL_CLIENT_PREFIX}testclient-new.html`;
const ENABLED = process.env.ENABLE_PINNED_CLIENT === '1';
const CLIENT_ROOT = path.resolve(process.env.PINNED_CLIENT_ROOT || '/opt/pokemon-showdown-client');
const CLIENT_PUBLIC_ROOT = path.join(CLIENT_ROOT, 'play.pokemonshowdown.com');
const DEFAULT_PLAYER_NAME = process.env.DEFAULT_PLAYER_NAME || 'Dolphin23';
const ACCESS_TOKEN = process.env.ACCESS_TOKEN || '';
const ACCESS_COOKIE = 'showdown_ai_access';
const ACCESS_DIGEST = ACCESS_TOKEN ? crypto.createHash('sha256').update(ACCESS_TOKEN).digest('hex') : '';

const MIME_TYPES = new Map([
  ['.css', 'text/css; charset=utf-8'],
  ['.gif', 'image/gif'],
  ['.html', 'text/html; charset=utf-8'],
  ['.ico', 'image/x-icon'],
  ['.jpeg', 'image/jpeg'],
  ['.jpg', 'image/jpeg'],
  ['.js', 'text/javascript; charset=utf-8'],
  ['.json', 'application/json; charset=utf-8'],
  ['.map', 'application/json; charset=utf-8'],
  ['.png', 'image/png'],
  ['.svg', 'image/svg+xml'],
  ['.txt', 'text/plain; charset=utf-8'],
  ['.webp', 'image/webp'],
  ['.woff', 'font/woff'],
  ['.woff2', 'font/woff2'],
]);

function parseCookies(req) {
  const cookies = {};
  for (const pair of String(req.headers.cookie || '').split(';')) {
    const index = pair.indexOf('=');
    if (index < 0) continue;
    try {
      cookies[pair.slice(0, index).trim()] = decodeURIComponent(pair.slice(index + 1).trim());
    } catch (_error) {
      return {};
    }
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

function writeBuffer(req, res, statusCode, contentType, payload, cacheControl) {
  const headers = {
    'cache-control': cacheControl,
    'content-length': payload.length,
    'content-type': contentType,
    'x-content-type-options': 'nosniff',
    'x-pokemon-showdown-client-source': 'pinned-local',
  };
  res.writeHead(statusCode, headers);
  if (req.method === 'HEAD') {
    res.end();
  } else {
    res.end(payload);
  }
}

function writeText(req, res, statusCode, message) {
  writeBuffer(req, res, statusCode, 'text/plain; charset=utf-8', Buffer.from(message), 'no-store');
}

function localPathname(req) {
  try {
    return new URL(req.url, 'http://localhost').pathname;
  } catch (_error) {
    return '';
  }
}

function resolveStaticFile(pathname) {
  let relative;
  try {
    relative = decodeURIComponent(pathname.slice(LOCAL_CLIENT_PREFIX.length));
  } catch (_error) {
    return null;
  }
  if (!relative || relative.includes('\0') || relative.includes('\\')) return null;
  const segments = relative.split('/');
  if (segments.some(segment => !segment || segment === '.' || segment === '..')) return null;
  const candidate = path.resolve(CLIENT_PUBLIC_ROOT, ...segments);
  if (!candidate.startsWith(`${CLIENT_PUBLIC_ROOT}${path.sep}`)) return null;
  return candidate;
}

function serveEntry(req, res) {
  const source = path.join(CLIENT_PUBLIC_ROOT, 'testclient-new.html');
  let html;
  try {
    html = fs.readFileSync(source, 'utf8');
  } catch (error) {
    writeText(req, res, 503, `Pinned client entry is unavailable: ${error.message}`);
    return;
  }
  const marker = '<script nomodule src="/js/lib/ps-polyfill.js"></script>';
  if (!html.includes(marker)) {
    writeText(req, res, 500, 'Pinned client entry could not be patched.');
    return;
  }
  const localMarker = '<script nomodule src="/local-client/js/lib/ps-polyfill.js"></script>';
  const patched = html.replace(marker, `${clientConfigInjection()}\n\t${localMarker}`);
  writeBuffer(req, res, 200, 'text/html; charset=utf-8', Buffer.from(patched), 'no-store');
}

function serveStatic(req, res, pathname) {
  const filename = resolveStaticFile(pathname);
  if (!filename) {
    writeText(req, res, 404, 'Pinned client file not found.');
    return;
  }
  let stat;
  try {
    stat = fs.statSync(filename);
  } catch (_error) {
    writeText(req, res, 404, 'Pinned client file not found.');
    return;
  }
  if (!stat.isFile()) {
    writeText(req, res, 404, 'Pinned client file not found.');
    return;
  }
  const contentType = MIME_TYPES.get(path.extname(filename).toLowerCase()) || 'application/octet-stream';
  writeBuffer(req, res, 200, contentType, fs.readFileSync(filename), 'public, max-age=31536000, immutable');
}

function handlePinnedClient(req, res) {
  const pathname = localPathname(req);
  const targetsLocalClient = pathname === '/local-client' || pathname.startsWith(LOCAL_CLIENT_PREFIX);
  if (!targetsLocalClient || !hasAccess(req)) return false;
  if (!ENABLED) {
    writeText(req, res, 404, 'Pinned client route is disabled.');
    return true;
  }
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    res.writeHead(405, { allow: 'GET, HEAD', 'cache-control': 'no-store' });
    res.end();
    return true;
  }
  if (pathname === '/local-client' || pathname === LOCAL_CLIENT_PREFIX || pathname === LOCAL_CLIENT_ENTRY) {
    serveEntry(req, res);
    return true;
  }
  serveStatic(req, res, pathname);
  return true;
}

if (path.basename(process.argv[1] || '') === 'launcher-server.js') {
  const createServer = http.createServer.bind(http);
  http.createServer = listener => createServer((req, res) => {
    if (handlePinnedClient(req, res)) return;
    listener(req, res);
  });
}

module.exports = {
  LOCAL_CLIENT_ENTRY,
  LOCAL_CLIENT_PREFIX,
  clientConfigInjection,
  handlePinnedClient,
  resolveStaticFile,
};
