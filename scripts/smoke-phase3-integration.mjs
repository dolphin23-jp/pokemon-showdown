#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const sleep = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));
const args = {
	debugUrl: 'http://127.0.0.1:9222',
	outputDir: '/tmp/phase3-integration',
	url: 'http://127.0.0.1:10008/index-new.html',
};
for (let index = 2; index < process.argv.length; index++) {
	const argument = process.argv[index];
	if (argument === '--debug-url') args.debugUrl = process.argv[++index];
	else if (argument === '--output-dir') args.outputDir = process.argv[++index];
	else if (argument === '--url') args.url = process.argv[++index];
	else throw new Error(`Unknown argument: ${argument}`);
}

async function findPageTarget() {
	const deadline = Date.now() + 30_000;
	let lastError = null;
	while (Date.now() < deadline) {
		try {
			const response = await fetch(`${args.debugUrl}/json`);
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
			}, {once: true});
			socket.addEventListener('error', event => {
				clearTimeout(timer);
				reject(new Error(`Chrome DevTools WebSocket error: ${event.message || 'unknown error'}`));
			}, {once: true});
			socket.addEventListener('message', event => {
				const message = JSON.parse(String(event.data));
				if (!message.id) return;
				const pending = this.pending.get(message.id);
				if (!pending) return;
				this.pending.delete(message.id);
				if (message.error) pending.reject(new Error(`${pending.method}: ${message.error.message}`));
				else pending.resolve(message.result || {});
			});
		});
	}
	send(method, params = {}) {
		if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
			return Promise.reject(new Error('Chrome DevTools WebSocket is not open'));
		}
		const id = this.nextId++;
		return new Promise((resolve, reject) => {
			this.pending.set(id, {method, resolve, reject});
			this.socket.send(JSON.stringify({id, method, params}));
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

function browserCall(client, callback, argument = null) {
	const callbackSource = JSON.stringify(`(${callback.toString()})`);
	const argumentSource = JSON.stringify(argument);
	return evaluate(client, `(async () => {
		const callback = (0, eval)(${callbackSource});
		return await callback(${argumentSource});
	})()`);
}

async function waitForPage(client, expression, label, timeout = 45_000) {
	const deadline = Date.now() + timeout;
	while (Date.now() < deadline) {
		if (await evaluate(client, expression)) return;
		await sleep(150);
	}
	throw new Error(`Timed out waiting for ${label}`);
}

async function captureScreenshot(client, filename) {
	const {data} = await client.send('Page.captureScreenshot', {
		format: 'png',
		captureBeyondViewport: false,
		fromSurface: true,
	});
	const filePath = path.join(args.outputDir, filename);
	fs.writeFileSync(filePath, Buffer.from(data, 'base64'));
	if (!fs.statSync(filePath).size) throw new Error(`Screenshot was empty: ${filePath}`);
}

function installBrowserHelpers() {
	window.__phase3Click = element => {
		if (!element) throw new Error('Attempted to click a missing element');
		element.scrollIntoView({block: 'center', inline: 'center'});
		element.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, cancelable: true, button: 0}));
		element.dispatchEvent(new MouseEvent('mouseup', {bubbles: true, cancelable: true, button: 0}));
		element.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, button: 0}));
		return element.textContent?.trim() || '';
	};
	return true;
}

function seedBattle() {
	const roomid = 'battle-t308-integration';
	window.PS.prefs.onepanel = true;
	window.PS.prefs.battlelayout = 'side-by-side-overlay';
	window.PS.user.name = 'Alice';
	window.PS.user.userid = 'alice';
	window.PS.user.named = true;
	window.__phase3Sent = [];
	window.PS.send = (message, targetRoom) => window.__phase3Sent.push({message, room: targetRoom || ''});
	window.__phase3InitialPokemon = [
		{
			ident: 'p1: Pikachu', details: 'Pikachu, L50', condition: '75/100', active: true,
			stats: {atk: 100, def: 100, spa: 120, spd: 100, spe: 120},
			moves: ['thunderbolt', 'quickattack'], baseAbility: 'static', ability: 'static',
			item: 'leftovers', pokeball: 'pokeball',
		},
		{
			ident: 'p1: Charizard', details: 'Charizard, L50', condition: '100/100', active: false,
			stats: {atk: 100, def: 100, spa: 120, spd: 100, spe: 100},
			moves: ['flamethrower'], baseAbility: 'blaze', ability: 'blaze', item: '', pokeball: 'pokeball',
		},
	];
	window.PS.receive([
		`>${roomid}`,
		'|init|battle',
		'|title|Alice vs. Bob',
		'|gametype|singles',
		'|player|p1|Alice|1|',
		'|player|p2|Bob|2|',
		'|teamsize|p1|2',
		'|teamsize|p2|1',
		'|gen|9',
		'|tier|[Gen 9] Custom Game',
		'|start',
		'|switch|p1a: Pikachu|Pikachu, L50|75/100',
		'|switch|p2a: Eevee|Eevee, L50|100/100',
		'|turn|1',
	].join('\n'));
	window.PS.focusRoom(roomid);
	const room = window.PS.rooms[roomid];
	room.width = 1000;
	room.height = 800;
	room.update(null);
	window.PS.update();
	return roomid;
}

function deliverInitialRequest(roomid) {
	const request = {
		active: [{moves: [
			{move: 'Thunderbolt', id: 'thunderbolt', pp: 24, maxpp: 24, target: 'normal', disabled: false},
			{move: 'Quick Attack', id: 'quickattack', pp: 48, maxpp: 48, target: 'normal', disabled: false},
		], canTerastallize: 'Electric'}],
		side: {name: 'Alice', id: 'p1', pokemon: window.__phase3InitialPokemon}, rqid: 1,
	};
	window.PS.receive(`>${roomid}\n|request|${JSON.stringify(request)}`);
	const room = window.PS.rooms[roomid];
	room.battle.seekTurn(Infinity);
	room.update(null);
	window.PS.update();
	return true;
}

function inspectBattleStart(roomid) {
	const root = document.querySelector(`#room-${roomid}`);
	if (!root) throw new Error(`Battle root missing: ${roomid}`);
	const controls = {
		battle: root.querySelector('button[data-cmd="/movemenu"]')?.textContent?.trim() || '',
		switch: root.querySelector('button[data-cmd="/switchmenu"]')?.textContent?.trim() || '',
		timer: root.querySelector('button[role="timer"]')?.textContent?.trim() || '',
	};
	if (controls.battle !== '対戦') throw new Error(`Battle label mismatch: ${JSON.stringify(controls)}`);
	if (controls.switch !== '交代') throw new Error(`Switch label mismatch: ${JSON.stringify(controls)}`);
	if (!controls.timer.includes('タイマー')) throw new Error(`Timer label mismatch: ${JSON.stringify(controls)}`);
	const residues = Object.values(controls).filter(value => ['Battle', 'Switch', 'Timer'].includes(value));
	if (residues.length) throw new Error(`English battle controls remain: ${residues.join(', ')}`);
	return {controls, residues, text: (root.textContent || '').trim()};
}

async function performSwitch(roomid) {
	const root = document.querySelector(`#room-${roomid}`);
	window.__phase3Click(root?.querySelector('button[data-cmd="/switchmenu"]'));
	await new Promise(resolve => setTimeout(resolve, 150));
	const button = root?.querySelector('button[data-cmd="/switch 2"]');
	const label = window.__phase3Click(button);
	await new Promise(resolve => setTimeout(resolve, 200));
	const sent = [...window.__phase3Sent];
	const choice = sent.find(entry => /(?:^|\s)\/choose\s+switch\s+2(?:\s|$)/.test(entry.message));
	if (!choice) throw new Error(`Switch control did not send /choose switch 2: ${JSON.stringify(sent)}`);
	return {label, dataCmd: button.dataset.cmd, outbound: choice};
}

async function applySwitchResult(roomid) {
	const room = window.PS.rooms[roomid];
	const pokemon = [
		{
			ident: 'p1: Pikachu', details: 'Pikachu, L50', condition: '75/100', active: false,
			stats: {atk: 100, def: 100, spa: 120, spd: 100, spe: 120},
			moves: ['thunderbolt', 'quickattack'], baseAbility: 'static', ability: 'static',
			item: 'leftovers', pokeball: 'pokeball',
		},
		{
			ident: 'p1: Charizard', details: 'Charizard, L50', condition: '100/100', active: true,
			stats: {atk: 100, def: 100, spa: 120, spd: 100, spe: 100},
			moves: ['flamethrower'], baseAbility: 'blaze', ability: 'blaze', item: '', pokeball: 'pokeball',
		},
	];
	const request = {
		active: [{moves: [
			{move: 'Flamethrower', id: 'flamethrower', pp: 24, maxpp: 24, target: 'normal', disabled: false},
		]}], side: {name: 'Alice', id: 'p1', pokemon}, rqid: 2,
	};
	window.PS.receive(`>${roomid}\n|switch|p1a: Charizard|Charizard, L50|100/100\n|turn|2\n|request|${JSON.stringify(request)}`);
	room.battle.seekTurn(Infinity);
	room.update(null);
	window.PS.update();
	await new Promise(resolve => setTimeout(resolve, 200));
	const text = document.querySelector(`#room-${roomid}`)?.textContent || '';
	if (!text.includes('リザードン')) throw new Error(`Japanese switched species missing: ${text}`);
	return {text: text.trim()};
}

async function performMove(roomid) {
	const root = document.querySelector(`#room-${roomid}`);
	const moveMenu = root?.querySelector('button[data-cmd="/movemenu"]');
	if (moveMenu) window.__phase3Click(moveMenu);
	await new Promise(resolve => setTimeout(resolve, 150));
	const button = root?.querySelector('button[data-cmd^="/move 1"]');
	const label = window.__phase3Click(button);
	await new Promise(resolve => setTimeout(resolve, 200));
	const sent = [...window.__phase3Sent];
	const choice = [...sent].reverse().find(entry => /(?:^|\s)\/choose\s+move\s+1(?:\s|$)/.test(entry.message));
	if (!choice) throw new Error(`Move control did not send /choose move 1: ${JSON.stringify(sent)}`);
	if (!label.includes('かえんほうしゃ')) throw new Error(`Japanese move label missing: ${label}`);
	return {label, dataCmd: button.dataset.cmd, outbound: choice};
}

async function applyMoveAndItemResult(roomid) {
	const room = window.PS.rooms[roomid];
	window.PS.receive([
		`>${roomid}`,
		'|move|p1a: Charizard|Flamethrower|p2a: Eevee',
		'|-damage|p2a: Eevee|70/100',
		'|move|p2a: Eevee|Tackle|p1a: Charizard',
		'|-damage|p1a: Charizard|85/100',
		'|switch|p1a: Pikachu|Pikachu, L50|75/100',
		'|-heal|p1a: Pikachu|81/100|[from] item: Leftovers',
		'|turn|3',
	].join('\n'));
	room.battle.seekTurn(Infinity);
	room.update(null);
	window.PS.update();
	await new Promise(resolve => setTimeout(resolve, 250));
	const root = document.querySelector(`#room-${roomid}`);
	const text = root?.textContent || '';
	const logText = root?.querySelector('.battle-log')?.textContent || text;
	if (!text.includes('かえんほうしゃ')) throw new Error(`Japanese move narration missing: ${text}`);
	if (!logText.includes('たべのこし')) throw new Error(`Japanese Leftovers effect missing: ${logText}`);
	if (/restored a little HP|using its Leftovers/i.test(logText)) {
		throw new Error(`English Leftovers narration remains: ${logText}`);
	}
	return {text: text.trim(), logText: logText.trim()};
}

async function openForfeitDialog(roomid) {
	window.PS.join('forfeitbattle', {parentRoomid: roomid});
	await new Promise(resolve => setTimeout(resolve, 250));
	const root = document.querySelector('#room-forfeitbattle');
	if (!root) throw new Error('Forfeit dialog did not open');
	const labels = {
		confirm: '対戦を降参すると負けになります。よろしいですか？',
		forfeitAndClose: '降参して閉じる',
		justForfeit: '降参する',
		cancel: 'キャンセル',
	};
	const text = root.textContent || '';
	for (const label of Object.values(labels)) {
		if (!text.includes(label)) throw new Error(`Forfeit label missing: ${label} / ${text}`);
	}
	for (const residue of ['Forfeiting makes you lose the battle', 'Forfeit and close', 'Just forfeit', 'Cancel']) {
		if (text.includes(residue)) throw new Error(`English forfeit chrome remains: ${residue}`);
	}
	const commands = [
		'/closeand /inopener /closeand /forfeit',
		'/closeand /inopener /forfeit',
		'/close',
	];
	for (const command of commands) {
		if (!root.querySelector(`button[data-cmd="${command}"]`)) throw new Error(`Forfeit command missing: ${command}`);
	}
	return {labels, commands, text: text.trim()};
}

async function submitForfeit(roomid) {
	const root = document.querySelector('#room-forfeitbattle');
	const button = root?.querySelector('button[data-cmd="/closeand /inopener /forfeit"]');
	window.__phase3Click(button);
	await new Promise(resolve => setTimeout(resolve, 200));
	const sent = [...window.__phase3Sent];
	const command = [...sent].reverse().find(entry => entry.message === '/forfeit' && entry.room === roomid);
	if (!command) throw new Error(`Forfeit control did not send canonical /forfeit: ${JSON.stringify(sent)}`);
	return command;
}

async function finishBattle(roomid) {
	window.PS.receive(`>${roomid}\n|win|Bob`);
	const room = window.PS.rooms[roomid];
	room.battle.seekTurn(Infinity);
	room.update(null);
	window.PS.update();
	await new Promise(resolve => setTimeout(resolve, 250));
	const root = document.querySelector(`#room-${roomid}`);
	const text = root?.textContent || '';
	for (const label of ['メインメニュー', '再戦']) {
		if (!text.includes(label)) throw new Error(`Japanese post-battle label missing: ${label} / ${text}`);
	}
	for (const residue of ['Main menu', 'Rematch']) {
		if (text.includes(residue)) throw new Error(`English post-battle chrome remains: ${residue}`);
	}
	return {text: text.trim()};
}

fs.mkdirSync(args.outputDir, {recursive: true});
const reportPath = path.join(args.outputDir, 'phase3-browser-integration.json');
const report = {
	phase: 'Phase 3',
	task: 'T3-08',
	verified: false,
	url: args.url,
	screenshots: [],
};
const target = await findPageTarget();
const client = new CDPClient(target.webSocketDebuggerUrl);
await client.connect();
try {
	await client.send('Page.enable');
	await client.send('Runtime.enable');
	await client.send('Emulation.setDeviceMetricsOverride', {
		width: 1280,
		height: 900,
		deviceScaleFactor: 1,
		mobile: false,
	});
	await client.send('Page.navigate', {url: args.url});
	await waitForPage(client, 'Boolean(window.PS && window.PS.roomTypes && window.PS.roomTypes.battle)', 'client battle modules');
	await browserCall(client, installBrowserHelpers);
	const roomid = await browserCall(client, seedBattle);
	await waitForPage(client, `Boolean(window.PS.rooms['${roomid}']?.battle)`, 'battle model');
	await browserCall(client, deliverInitialRequest, roomid);
	await waitForPage(client, `Boolean(document.querySelector('#room-${roomid} button[data-cmd="/movemenu"]') && document.querySelector('#room-${roomid} button[data-cmd="/switchmenu"]'))`, 'battle overlay controls');

	report.start = await browserCall(client, inspectBattleStart, roomid);
	await captureScreenshot(client, 'phase3-battle-start.png');
	report.screenshots.push('phase3-battle-start.png');

	report.switch = await browserCall(client, performSwitch, roomid);
	report.switchResult = await browserCall(client, applySwitchResult, roomid);
	await captureScreenshot(client, 'phase3-battle-switch.png');
	report.screenshots.push('phase3-battle-switch.png');

	report.move = await browserCall(client, performMove, roomid);
	report.battleText = await browserCall(client, applyMoveAndItemResult, roomid);
	await captureScreenshot(client, 'phase3-battle-leftovers.png');
	report.screenshots.push('phase3-battle-leftovers.png');

	report.forfeitDialog = await browserCall(client, openForfeitDialog, roomid);
	await captureScreenshot(client, 'phase3-forfeit-dialog.png');
	report.screenshots.push('phase3-forfeit-dialog.png');
	report.forfeitCommand = await browserCall(client, submitForfeit, roomid);

	report.result = await browserCall(client, finishBattle, roomid);
	await captureScreenshot(client, 'phase3-battle-result.png');
	report.screenshots.push('phase3-battle-result.png');

	report.outbound = await evaluate(client, 'window.__phase3Sent');
	report.verified = true;
	fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + '\n');
	console.log(JSON.stringify(report, null, 2));
} catch (error) {
	report.error = error?.stack || String(error);
	fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + '\n');
	throw error;
} finally {
	client.close();
}
