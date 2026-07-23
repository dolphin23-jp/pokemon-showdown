#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';

function parseArgs(argv) {
	const args = {
		cookieJar: '',
		debugUrl: 'http://127.0.0.1:9222',
		outputDir: '/tmp/japanese-battle-chrome',
		packedTeam: '',
		url: 'http://127.0.0.1:10003/client.html',
	};
	for (let index = 2; index < argv.length; index++) {
		const argument = argv[index];
		if (argument === '--cookie-jar') args.cookieJar = argv[++index];
		else if (argument === '--debug-url') args.debugUrl = argv[++index];
		else if (argument === '--output-dir') args.outputDir = argv[++index];
		else if (argument === '--packed-team') args.packedTeam = argv[++index];
		else if (argument === '--url') args.url = argv[++index];
		else throw new Error(`Unknown argument: ${argument}`);
	}
	if (!args.cookieJar) throw new Error('--cookie-jar is required');
	if (!args.packedTeam) throw new Error('--packed-team is required');
	return args;
}

const sleep = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));

async function findPageTarget(debugUrl) {
	const deadline = Date.now() + 30_000;
	let lastError = null;
	while (Date.now() < deadline) {
		try {
			const response = await fetch(`${debugUrl}/json`);
			if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
			const targets = await response.json();
			const page = targets.find(target => target.type === 'page' && target.webSocketDebuggerUrl);
			if (page) return page;
		} catch (error) {
			lastError = error;
		}
		await sleep(250);
	}
	throw new Error(`Chrome DevTools page target unavailable: ${lastError || 'timed out'}`);
}

class CDPClient {
	constructor(url) {
		this.url = url;
		this.nextId = 1;
		this.pending = new Map();
		this.socket = null;
	}

	async connect() {
		await new Promise((resolve, reject) => {
			const socket = new WebSocket(this.url);
			this.socket = socket;
			const timer = setTimeout(() => reject(new Error('Timed out connecting to Chrome DevTools')), 15_000);
			socket.addEventListener('open', () => {
				clearTimeout(timer);
				resolve();
			}, { once: true });
			socket.addEventListener('error', event => {
				clearTimeout(timer);
				reject(new Error(`Chrome DevTools WebSocket error: ${event.message || 'unknown error'}`));
			}, { once: true });
			socket.addEventListener('message', event => this.handleMessage(event));
			socket.addEventListener('close', () => {
				for (const pending of this.pending.values()) {
					pending.reject(new Error('Chrome DevTools WebSocket closed'));
				}
				this.pending.clear();
			});
		});
	}

	handleMessage(event) {
		const message = JSON.parse(String(event.data));
		if (!message.id) return;
		const pending = this.pending.get(message.id);
		if (!pending) return;
		this.pending.delete(message.id);
		if (message.error) pending.reject(new Error(`${pending.method}: ${message.error.message}`));
		else pending.resolve(message.result || {});
	}

	send(method, params = {}) {
		if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
			return Promise.reject(new Error('Chrome DevTools WebSocket is not open'));
		}
		const id = this.nextId++;
		return new Promise((resolve, reject) => {
			this.pending.set(id, { method, resolve, reject });
			this.socket.send(JSON.stringify({ id, method, params }));
		});
	}

	close() {
		this.socket?.close();
	}
}

async function evaluate(client, expression) {
	const response = await client.send('Runtime.evaluate', {
		expression,
		awaitPromise: true,
		returnByValue: true,
		userGesture: true,
	});
	if (response.exceptionDetails) {
		const description = response.exceptionDetails.exception?.description || response.exceptionDetails.text;
		throw new Error(`Browser evaluation failed: ${description}`);
	}
	return response.result?.value;
}

async function browserCall(client, callback, argument = null) {
	return evaluate(client, `(${callback.toString()})(${JSON.stringify(argument)})`);
}

async function waitForPage(client, expression, label, timeout = 60_000) {
	const deadline = Date.now() + timeout;
	while (Date.now() < deadline) {
		if (await evaluate(client, expression)) return;
		await sleep(150);
	}
	throw new Error(`Timed out waiting for ${label}`);
}

async function captureScreenshot(client, filePath) {
	const { data } = await client.send('Page.captureScreenshot', {
		format: 'png',
		captureBeyondViewport: false,
		fromSurface: true,
	});
	fs.writeFileSync(filePath, Buffer.from(data, 'base64'));
	if (!fs.statSync(filePath).size) throw new Error(`Screenshot was empty: ${filePath}`);
}

function readCookieJar(filePath, targetUrl) {
	const url = new URL(targetUrl);
	const cookies = [];
	for (const rawLine of fs.readFileSync(filePath, 'utf8').split(/\r?\n/)) {
		let line = rawLine;
		let httpOnly = false;
		if (line.startsWith('#HttpOnly_')) {
			httpOnly = true;
			line = line.slice('#HttpOnly_'.length);
		} else if (!line || line.startsWith('#')) {
			continue;
		}
		const fields = line.split('\t');
		if (fields.length < 7) continue;
		const [domain, , cookiePath, secure, , name, value] = fields;
		cookies.push({
			domain: domain.replace(/^\./, ''),
			httpOnly,
			name,
			path: cookiePath || '/',
			secure: secure === 'TRUE',
			url: `${url.protocol}//${url.host}${cookiePath || '/'}`,
			value,
		});
	}
	if (!cookies.length) throw new Error(`No cookies found in ${filePath}`);
	return cookies;
}

async function installBrowserHelpers() {
	const delay = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));
	const waitFor = async (predicate, label, timeout = 60_000) => {
		const deadline = Date.now() + timeout;
		let lastError = null;
		while (Date.now() < deadline) {
			try {
				const value = predicate();
				if (value) return value;
			} catch (error) {
				lastError = error;
			}
			await delay(100);
		}
		throw new Error(`Timed out waiting for ${label}${lastError ? `: ${lastError.message}` : ''}`);
	};
	const click = element => {
		if (!element) throw new Error('Attempted to click a missing element');
		element.scrollIntoView({ block: 'center', inline: 'center' });
		element.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, button: 0 }));
		element.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, button: 0 }));
		element.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 }));
	};
	const visibleText = element => (element?.innerText || element?.textContent || '').replace(/\s+/g, ' ').trim();
	window.__battleChromeSmoke = { click, delay, visibleText, waitFor };
	return true;
}

async function initializeClient({ packedTeam }) {
	const { waitFor } = window.__battleChromeSmoke;
	await waitFor(() => window.PS?.connection?.connected, 'Showdown connection');
	if (!window.__battleChromeSent) {
		window.__battleChromeSent = [];
		const originalSend = window.PS.send.bind(window.PS);
		window.PS.send = message => {
			window.__battleChromeSent.push(String(message));
			return originalSend(message);
		};
	}
	window.PS.prefs.set('battlelayout', 'side-by-side-overlay');
	window.PS.send('/trn BattleChromeViewer,0,');
	await waitFor(() => window.PS.user?.named && window.PS.user.userid === 'battlechromeviewer', 'local login');
	window.PS.send('/updatesettings ' + JSON.stringify({ language: 'japanese' }));
	window.PS.send('/utm ' + packedTeam);
	return true;
}

async function verifyBattleList() {
	const { visibleText, waitFor } = window.__battleChromeSmoke;
	window.PS.join('battles');
	await waitFor(() => window.PS.rooms?.battles && document.querySelector('#room-battles'), 'battles room');
	const root = document.querySelector('#room-battles');
	const input = await waitFor(
		() => root.querySelector('input[name="prefixsearch"]'),
		'battle spectator search input'
	);
	const button = root.querySelector('form.search button[type="submit"]');
	if (input.getAttribute('placeholder') !== 'ユーザー名（前方一致）') {
		throw new Error(`Unexpected search placeholder: ${input.getAttribute('placeholder')}`);
	}
	if (visibleText(button) !== '検索') throw new Error(`Unexpected search button: ${visibleText(button)}`);
	return {
		placeholder: input.getAttribute('placeholder'),
		searchButton: visibleText(button),
	};
}

async function startBattle() {
	const { waitFor } = window.__battleChromeSmoke;
	Object.defineProperty(document, 'hasFocus', { configurable: true, value: () => false });
	window.PS.send('/challenge FoulPlayAI,gen9nationaldexallgenerationsbss');
	const room = await waitFor(
		() => Object.values(window.PS.rooms).find(candidate => candidate?.type === 'battle' && candidate.side),
		'player battle room',
		90_000
	);
	window.PS.focusRoom(room.id);
	await waitFor(() => room.request?.requestType === 'team', 'team preview request', 90_000);
	return room.id;
}

async function inspectTeamPreview(roomid) {
	const { visibleText, waitFor } = window.__battleChromeSmoke;
	const room = window.PS.rooms[roomid];
	const root = await waitFor(() => document.querySelector(`#room-${roomid}`), 'battle panel');
	await waitFor(() => root.querySelector('button[data-cmd="/switch 1"]'), 'team preview controls');
	const text = visibleText(root);
	if (!text.includes('チーム')) throw new Error(`Missing Japanese Team label: ${text}`);
	if (!text.includes('先発を選択')) throw new Error(`Missing Japanese lead prompt: ${text}`);
	await waitFor(
		() => room.notifications?.some(notification => notification.title === '選出してください'),
		'Japanese team preview notification'
	);
	const notification = room.notifications.find(item => item.title === '選出してください');
	return {
		commands: [...root.querySelectorAll('button[data-cmd^="/switch "]')].map(button => button.getAttribute('data-cmd')),
		notification: { title: notification.title, body: notification.body },
		text,
	};
}

async function chooseTeam(roomid) {
	const { waitFor } = window.__battleChromeSmoke;
	const room = window.PS.rooms[roomid];
	room.send('/team 123456');
	await waitFor(() => room.request?.requestType === 'move', 'turn-one move request', 90_000);
	await waitFor(() => document.querySelector(`#room-${roomid} button[data-cmd="/movemenu"]`), 'overlay battle controls');
	return true;
}

async function inspectMoveAndSwitch(roomid) {
	const { click, visibleText, waitFor } = window.__battleChromeSmoke;
	const room = window.PS.rooms[roomid];
	const root = document.querySelector(`#room-${roomid}`);
	const moveMenuButton = await waitFor(() => root.querySelector('button[data-cmd="/movemenu"]'), 'Battle menu button');
	const switchMenuButton = await waitFor(() => root.querySelector('button[data-cmd="/switchmenu"]'), 'Switch menu button');
	if (visibleText(moveMenuButton) !== '対戦') throw new Error(`Unexpected Battle button: ${visibleText(moveMenuButton)}`);
	if (visibleText(switchMenuButton) !== '交代') throw new Error(`Unexpected Switch button: ${visibleText(switchMenuButton)}`);

	click(moveMenuButton);
	await waitFor(() => root.querySelector('.movecontrols button[data-cmd^="/move "]'), 'opened move menu');
	const movePanelText = visibleText(root.querySelector('.movecontrols'));

	click(await waitFor(() => root.querySelector('button[data-cmd="/switchmenu"]'), 'Switch menu button after move open'));
	await waitFor(() => root.querySelector('.switchcontrols button[data-cmd^="/switch "]'), 'opened switch menu');
	const switchPanelText = visibleText(root.querySelector('.switchcontrols'));

	click(await waitFor(() => root.querySelector('button[data-cmd="/movemenu"]'), 'Battle menu button after switch open'));
	const moveButton = await waitFor(
		() => [...root.querySelectorAll('.movecontrols button[data-cmd^="/move "]')].find(button => !button.disabled),
		'enabled move button'
	);
	const selectedMoveCommand = moveButton.getAttribute('data-cmd');
	click(moveButton);
	const cancelButton = await waitFor(() => root.querySelector('button[data-cmd="/cancel"]'), 'cancel button after move choice');
	const cancelText = visibleText(cancelButton);
	if (cancelText !== 'キャンセル') throw new Error(`Unexpected Cancel button: ${cancelText}`);
	click(cancelButton);
	await waitFor(() => room.request?.requestType === 'move' && root.querySelector('button[data-cmd="/movemenu"]'), 'move controls after cancel');

	await waitFor(
		() => room.notifications?.some(notification => notification.title === '技を選んでください'),
		'Japanese move notification'
	);
	const moveNotification = room.notifications.find(notification => notification.title === '技を選んでください');
	return {
		battleCommand: moveMenuButton.getAttribute('data-cmd'),
		battleText: visibleText(moveMenuButton),
		cancelCommand: cancelButton.getAttribute('data-cmd'),
		cancelText,
		moveNotification: { title: moveNotification.title, body: moveNotification.body },
		movePanelText,
		selectedMoveCommand,
		switchCommand: switchMenuButton.getAttribute('data-cmd'),
		switchPanelText,
		switchText: visibleText(switchMenuButton),
	};
}

async function finishBattle(roomid) {
	const { visibleText, waitFor } = window.__battleChromeSmoke;
	const room = window.PS.rooms[roomid];
	room.send('/forfeit');
	await waitFor(() => room.battle?.ended, 'battle end', 45_000);
	const root = document.querySelector(`#room-${roomid}`);
	await waitFor(() => root.querySelector('button[data-cmd="/close"]'), 'ended battle controls');
	const text = visibleText(root.querySelector('.battle-controls'));
	for (const expected of ['メインメニュー', '再戦', 'リプレイ']) {
		if (!text.includes(expected)) throw new Error(`Missing ended-battle label ${expected}: ${text}`);
	}
	return { text };
}

async function main() {
	const args = parseArgs(process.argv);
	fs.mkdirSync(args.outputDir, { recursive: true });
	const packedTeam = fs.readFileSync(args.packedTeam, 'utf8').trim();
	if (!packedTeam) throw new Error('Packed team is empty');

	const target = await findPageTarget(args.debugUrl);
	const client = new CDPClient(target.webSocketDebuggerUrl);
	await client.connect();
	try {
		await client.send('Page.enable');
		await client.send('Runtime.enable');
		await client.send('Network.enable');
		await client.send('Emulation.setDeviceMetricsOverride', {
			deviceScaleFactor: 1,
			height: 900,
			mobile: false,
			width: 1280,
		});
		for (const cookie of readCookieJar(args.cookieJar, args.url)) {
			const result = await client.send('Network.setCookie', cookie);
			if (result.success === false) throw new Error(`Could not set access cookie ${cookie.name}`);
		}
		await client.send('Page.navigate', { url: args.url });
		await waitForPage(client, 'document.readyState === "complete"', 'client page load');
		await browserCall(client, installBrowserHelpers);
		await browserCall(client, initializeClient, { packedTeam });

		const report = { verified: false };
		report.battleList = await browserCall(client, verifyBattleList);
		await captureScreenshot(client, path.join(args.outputDir, 'japanese-battle-chrome-battles.png'));

		report.roomid = await browserCall(client, startBattle);
		report.teamPreview = await browserCall(client, inspectTeamPreview, report.roomid);
		await captureScreenshot(client, path.join(args.outputDir, 'japanese-battle-chrome-team-preview.png'));

		await browserCall(client, chooseTeam, report.roomid);
		report.controls = await browserCall(client, inspectMoveAndSwitch, report.roomid);
		await browserCall(client, async roomid => {
			const { click, waitFor } = window.__battleChromeSmoke;
			const root = document.querySelector(`#room-${roomid}`);
			click(await waitFor(() => root.querySelector('button[data-cmd="/movemenu"]'), 'move menu for screenshot'));
			await waitFor(() => root.querySelector('.movecontrols button[data-cmd^="/move "]'), 'move menu screenshot state');
			return true;
		}, report.roomid);
		await captureScreenshot(client, path.join(args.outputDir, 'japanese-battle-chrome-move-menu.png'));
		await browserCall(client, async roomid => {
			const { click, waitFor } = window.__battleChromeSmoke;
			const root = document.querySelector(`#room-${roomid}`);
			click(await waitFor(() => root.querySelector('button[data-cmd="/switchmenu"]'), 'switch menu for screenshot'));
			await waitFor(() => root.querySelector('.switchcontrols button[data-cmd^="/switch "]'), 'switch menu screenshot state');
			return true;
		}, report.roomid);
		await captureScreenshot(client, path.join(args.outputDir, 'japanese-battle-chrome-switch-menu.png'));

		report.ended = await browserCall(client, finishBattle, report.roomid);
		await captureScreenshot(client, path.join(args.outputDir, 'japanese-battle-chrome-ended.png'));
		report.sent = await evaluate(client, 'window.__battleChromeSent');
		report.verified = true;
		fs.writeFileSync(
			path.join(args.outputDir, 'japanese-battle-chrome-report.json'),
			`${JSON.stringify(report, null, 2)}\n`
		);
		console.log(JSON.stringify(report, null, 2));
	} finally {
		client.close();
	}
}

main().catch(error => {
	console.error(error?.stack || error);
	process.exitCode = 1;
});
