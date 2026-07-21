'use strict';

const fs = require('fs');
const path = require('path');

const CLIENT_ENTRY = '/client.html';
const LOCAL_CLIENT_PREFIX = '/local-client/';
const LOCAL_CLIENT_ENTRY = `${LOCAL_CLIENT_PREFIX}testclient-new.html`;
const CLIENT_ROOT = path.resolve(process.env.PINNED_CLIENT_ROOT || '/opt/pokemon-showdown-client');
const CLIENT_PUBLIC_ROOT = path.join(CLIENT_ROOT, 'play.pokemonshowdown.com');
const DEFAULT_PLAYER_NAME = process.env.DEFAULT_PLAYER_NAME || 'Dolphin23';

const PUBLIC_PREFIXES = ['/data/', '/js/', '/src/', '/style/'];
const PUBLIC_FILES = new Set(['/favicon.ico', '/favicon-256.png']);
const ROOT_FILES = new Map([
	['/config/config.js', path.join(CLIENT_ROOT, 'config', 'config.js')],
	['/config/testclient-key.js', path.join(CLIENT_ROOT, 'config', 'testclient-key.js')],
]);

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
	res.writeHead(statusCode, {
		'cache-control': cacheControl,
		'content-length': payload.length,
		'content-type': contentType,
		'x-content-type-options': 'nosniff',
		'x-pokemon-showdown-client-source': 'pinned-local',
	});
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
	} catch {
		return '';
	}
}

function safePath(root, relative) {
	let decoded;
	try {
		decoded = decodeURIComponent(relative);
	} catch {
		return null;
	}
	if (!decoded || decoded.includes('\0') || decoded.includes('\\')) return null;
	const segments = decoded.split('/');
	if (segments.some(segment => !segment || segment === '.' || segment === '..')) return null;
	const candidate = path.resolve(root, ...segments);
	if (!candidate.startsWith(`${root}${path.sep}`)) return null;
	return candidate;
}

function resolveStaticFile(pathname) {
	if (pathname.startsWith(LOCAL_CLIENT_PREFIX)) {
		return safePath(CLIENT_PUBLIC_ROOT, pathname.slice(LOCAL_CLIENT_PREFIX.length));
	}
	if (ROOT_FILES.has(pathname)) return ROOT_FILES.get(pathname);
	if (PUBLIC_FILES.has(pathname)) return safePath(CLIENT_PUBLIC_ROOT, pathname.slice(1));
	const prefix = PUBLIC_PREFIXES.find(candidate => pathname.startsWith(candidate));
	if (!prefix) return null;
	return safePath(CLIENT_PUBLIC_ROOT, pathname.slice(1));
}

function patchEntry(html) {
	const marker = '<script nomodule src="/js/lib/ps-polyfill.js"></script>';
	if (!html.includes(marker)) throw new Error('Pinned client entry does not contain the injection marker.');
	return html
		.replace('https://play.pokemonshowdown.com/favicon-256.png', '/favicon-256.png')
		.replace('https://play.pokemonshowdown.com/config/config.js', '/config/config.js')
		.replace(
			"src.replace(/.*\\/(data|js)\\//g, 'https://play.pokemonshowdown.com/$1/');",
			"src.replace(/.*\\/(data|js)\\//g, '/$1/');"
		)
		.replace("Net.defaultRoute = 'https://play.pokemonshowdown.com';", 'Net.defaultRoute = location.origin;')
		.replace('https://play.pokemonshowdown.com/data/pokedex-mini.js', '/data/pokedex-mini.js')
		.replace('https://play.pokemonshowdown.com/data/pokedex-mini-bw.js', '/data/pokedex-mini-bw.js')
		.replace(marker, `${clientConfigInjection()}\n\t${marker}`);
}

function serveEntry(req, res) {
	const source = path.join(CLIENT_PUBLIC_ROOT, 'testclient-new.html');
	let html;
	try {
		html = patchEntry(fs.readFileSync(source, 'utf8'));
	} catch (error) {
		writeText(req, res, 503, `Pinned client entry is unavailable: ${error.message}`);
		return;
	}
	writeBuffer(req, res, 200, 'text/html; charset=utf-8', Buffer.from(html), 'no-store');
}

function serveStatic(req, res, pathname) {
	const filename = resolveStaticFile(pathname);
	if (!filename) return false;
	let stat;
	try {
		stat = fs.statSync(filename);
	} catch {
		writeText(req, res, 404, 'Pinned client file not found.');
		return true;
	}
	if (!stat.isFile()) {
		writeText(req, res, 404, 'Pinned client file not found.');
		return true;
	}
	const contentType = MIME_TYPES.get(path.extname(filename).toLowerCase()) || 'application/octet-stream';
	writeBuffer(req, res, 200, contentType, fs.readFileSync(filename), 'public, max-age=31536000, immutable');
	return true;
}

function handlePinnedClient(req, res) {
	const pathname = localPathname(req);
	const isEntry = pathname === CLIENT_ENTRY || pathname === '/local-client' ||
		pathname === LOCAL_CLIENT_PREFIX || pathname === LOCAL_CLIENT_ENTRY;
	const isStatic = resolveStaticFile(pathname) !== null;
	if (!isEntry && !isStatic) return false;
	if (req.method !== 'GET' && req.method !== 'HEAD') {
		res.writeHead(405, { allow: 'GET, HEAD', 'cache-control': 'no-store' });
		res.end();
		return true;
	}
	if (isEntry) {
		serveEntry(req, res);
		return true;
	}
	return serveStatic(req, res, pathname);
}

module.exports = {
	CLIENT_ENTRY,
	LOCAL_CLIENT_ENTRY,
	LOCAL_CLIENT_PREFIX,
	clientConfigInjection,
	handlePinnedClient,
	patchEntry,
	resolveStaticFile,
};
