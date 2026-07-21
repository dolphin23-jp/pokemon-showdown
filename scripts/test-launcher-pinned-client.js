'use strict';

const assert = require('assert/strict');
const crypto = require('crypto');
const fs = require('fs');
const http = require('http');
const net = require('net');
const os = require('os');
const path = require('path');
const { spawn } = require('child_process');

const root = path.resolve(__dirname, '..');
const launcher = path.join(__dirname, 'launcher-server.js');
const preload = path.join(__dirname, 'pinned-client-preload.js');

function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const address = server.address();
      server.close(error => error ? reject(error) : resolve(address.port));
    });
  });
}

function request(port, requestPath, options = {}) {
  return new Promise((resolve, reject) => {
    const req = http.request({
      hostname: '127.0.0.1',
      port,
      path: requestPath,
      method: options.method || 'GET',
      headers: options.headers || {},
    }, res => {
      const chunks = [];
      res.on('data', chunk => chunks.push(chunk));
      res.on('end', () => resolve({
        body: Buffer.concat(chunks),
        headers: res.headers,
        statusCode: res.statusCode,
      }));
    });
    req.once('error', reject);
    req.end(options.body || undefined);
  });
}

async function waitForHealth(port, child) {
  for (let attempt = 0; attempt < 100; attempt++) {
    if (child.exitCode !== null) throw new Error(`Launcher exited with ${child.exitCode}`);
    try {
      const response = await request(port, '/health');
      if (response.statusCode === 200) return;
    } catch (_error) {}
    await new Promise(resolve => setTimeout(resolve, 25));
  }
  throw new Error('Launcher did not become healthy');
}

async function stop(child) {
  if (child.exitCode !== null) return;
  child.kill('SIGTERM');
  await Promise.race([
    new Promise(resolve => child.once('exit', resolve)),
    new Promise(resolve => setTimeout(resolve, 2000)),
  ]);
  if (child.exitCode === null) child.kill('SIGKILL');
}

function startLauncher({ clientRoot, enabled, port, accessToken = '' }) {
  const child = spawn(process.execPath, [launcher], {
    cwd: root,
    env: {
      ...process.env,
      ACCESS_TOKEN: accessToken,
      DEFAULT_PLAYER_NAME: 'FallbackUser',
      ENABLE_PINNED_CLIENT: enabled ? '1' : '0',
      LAUNCHER_PORT: String(port),
      NODE_OPTIONS: `--require=${preload}`,
      PINNED_CLIENT_ROOT: clientRoot,
      SHOWDOWN_PORT: '65534',
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let diagnostics = '';
  child.stdout.on('data', chunk => { diagnostics += chunk; });
  child.stderr.on('data', chunk => { diagnostics += chunk; });
  child.diagnostics = () => diagnostics;
  return child;
}

function createFixture() {
  const clientRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'pinned-client-'));
  const publicRoot = path.join(clientRoot, 'play.pokemonshowdown.com');
  fs.mkdirSync(path.join(publicRoot, 'js', 'lib'), { recursive: true });
  fs.mkdirSync(path.join(publicRoot, 'style'), { recursive: true });
  fs.writeFileSync(path.join(publicRoot, 'testclient-new.html'), `<!doctype html>
<html><head><link rel="stylesheet" href="style/client2.css"></head><body>
<script nomodule src="/js/lib/ps-polyfill.js"></script>
<script src="js/client-main.js"></script>
</body></html>\n`);
  fs.writeFileSync(path.join(publicRoot, 'js', 'client-main.js'), 'globalThis.__localClient = true;\n');
  fs.writeFileSync(path.join(publicRoot, 'js', 'lib', 'ps-polyfill.js'), 'globalThis.__polyfill = true;\n');
  fs.writeFileSync(path.join(publicRoot, 'style', 'client2.css'), 'body { display: block; }\n');
  return clientRoot;
}

async function main() {
  const clientRoot = createFixture();
  const accessToken = 'test-access-token';
  const accessDigest = crypto.createHash('sha256').update(accessToken).digest('hex');
  const cookie = `showdown_ai_access=${accessDigest}`;

  const enabledPort = await freePort();
  const enabled = startLauncher({ clientRoot, enabled: true, port: enabledPort, accessToken });
  try {
    await waitForHealth(enabledPort, enabled);

    const unauthorized = await request(enabledPort, '/local-client/testclient-new.html');
    assert.equal(unauthorized.statusCode, 401, 'The local client must respect the existing access gate');
    assert.match(unauthorized.body.toString(), /このサーバーは個人用です/);

    const entry = await request(enabledPort, '/local-client/testclient-new.html', {
      headers: { cookie },
    });
    assert.equal(entry.statusCode, 200, enabled.diagnostics());
    assert.equal(entry.headers['x-pokemon-showdown-client-source'], 'pinned-local');
    assert.equal(entry.headers['cache-control'], 'no-store');
    const html = entry.body.toString();
    assert.match(html, /prefix: '\/showdown'/);
    assert.match(html, /ps\.send\('\/trn ' \+ cleaned \+ ',0,'\)/);
    assert.match(html, /\/updatesettings/);
    assert.match(html, /language: 'japanese'/);
    assert.match(html, /src="\/local-client\/js\/lib\/ps-polyfill\.js"/);

    const asset = await request(enabledPort, '/local-client/js/client-main.js', {
      headers: { cookie },
    });
    assert.equal(asset.statusCode, 200);
    assert.equal(asset.headers['content-type'], 'text/javascript; charset=utf-8');
    assert.equal(asset.headers['cache-control'], 'public, max-age=31536000, immutable');
    assert.equal(asset.body.toString(), 'globalThis.__localClient = true;\n');

    const head = await request(enabledPort, '/local-client/style/client2.css', {
      method: 'HEAD',
      headers: { cookie },
    });
    assert.equal(head.statusCode, 200);
    assert.equal(head.body.length, 0);

    const traversal = await request(enabledPort, '/local-client/%2e%2e%2fsecret.txt', {
      headers: { cookie },
    });
    assert.equal(traversal.statusCode, 404);

    const method = await request(enabledPort, '/local-client/js/client-main.js', {
      method: 'POST',
      headers: { cookie },
    });
    assert.equal(method.statusCode, 405);
    assert.equal(method.headers.allow, 'GET, HEAD');
  } finally {
    await stop(enabled);
  }

  const disabledPort = await freePort();
  const disabled = startLauncher({ clientRoot, enabled: false, port: disabledPort });
  try {
    await waitForHealth(disabledPort, disabled);
    const response = await request(disabledPort, '/local-client/testclient-new.html');
    assert.equal(response.statusCode, 404, disabled.diagnostics());
    assert.match(response.body.toString(), /route is disabled/);
  } finally {
    await stop(disabled);
    fs.rmSync(clientRoot, { recursive: true, force: true });
  }

  console.log('Pinned client route test passed.');
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
