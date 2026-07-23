#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const args = {debugUrl: 'http://127.0.0.1:9222', outputDir: '/tmp/japanese-battle-chrome', url: 'http://127.0.0.1:10005/index-new.html'};
for (let i = 2; i < process.argv.length; i++) {
	const arg = process.argv[i];
	if (arg === '--debug-url') args.debugUrl = process.argv[++i];
	else if (arg === '--output-dir') args.outputDir = process.argv[++i];
	else if (arg === '--url') args.url = process.argv[++i];
	else throw new Error(`Unknown argument: ${arg}`);
}
async function findPageTarget() {
	const deadline = Date.now() + 30000;
	while (Date.now() < deadline) {
		try {
			const targets = await (await fetch(`${args.debugUrl}/json`)).json();
			const page = targets.find(target => target.type === 'page' && target.webSocketDebuggerUrl);
			if (page) return page;
		} catch {}
		await sleep(200);
	}
	throw new Error('Chrome DevTools page target unavailable');
}
class CDP {
	constructor(url) { this.url = url; this.id = 1; this.pending = new Map(); }
	async connect() {
		await new Promise((resolve, reject) => {
			this.ws = new WebSocket(this.url);
			this.ws.addEventListener('open', resolve, {once: true});
			this.ws.addEventListener('error', reject, {once: true});
			this.ws.addEventListener('message', event => {
				const msg = JSON.parse(String(event.data));
				if (!msg.id) return;
				const pending = this.pending.get(msg.id);
				if (!pending) return;
				this.pending.delete(msg.id);
				if (msg.error) pending.reject(new Error(`${pending.method}: ${msg.error.message}`));
				else pending.resolve(msg.result || {});
			});
		});
	}
	send(method, params = {}) {
		const id = this.id++;
		return new Promise((resolve, reject) => {
			this.pending.set(id, {method, resolve, reject});
			this.ws.send(JSON.stringify({id, method, params}));
		});
	}
	close() { this.ws?.close(); }
}
async function evaluate(client, expression) {
	const result = await client.send('Runtime.evaluate', {expression, awaitPromise: true, returnByValue: true, userGesture: true});
	if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
	return result.result?.value;
}
function call(client, fn, value = null) {
	const source = JSON.stringify(`(${fn.toString()})`);
	const argument = JSON.stringify(value);
	return evaluate(client, `(async () => {
		const callback = (0, eval)(${source});
		return await callback(${argument});
	})()`);
}
async function wait(client, expression, label, timeout = 45000) {
	const deadline = Date.now() + timeout;
	while (Date.now() < deadline) {
		if (await evaluate(client, expression)) return;
		await sleep(120);
	}
	throw new Error(`Timed out waiting for ${label}`);
}
async function screenshot(client, filename) {
	const {data} = await client.send('Page.captureScreenshot', {format: 'png', captureBeyondViewport: false, fromSurface: true});
	fs.writeFileSync(path.join(args.outputDir, filename), Buffer.from(data, 'base64'));
}
function installBrowserHelpers() {
	window.__battleChromeClick = selector => {
		const element = document.querySelector(selector);
		if (!element) throw new Error(`Missing element: ${selector}`);
		element.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, cancelable: true, button: 0}));
		element.dispatchEvent(new MouseEvent('mouseup', {bubbles: true, cancelable: true, button: 0}));
		element.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, button: 0}));
		return element.textContent.trim();
	};
	return true;
}
function seedBattle() {
	const roomid = 'battle-t305-smoke';
	window.PS.prefs.onepanel = true;
	window.PS.prefs.battlelayout = 'side-by-side-overlay';
	window.PS.user.name = 'Alice';
	window.PS.user.userid = 'alice';
	window.PS.user.named = true;
	window.__battleChromeSent = [];
	window.PS.send = (message, targetRoom) => window.__battleChromeSent.push({message, room: targetRoom || ''});
	window.__battleChromePokemon = [
		{ident: 'p1: Pikachu', details: 'Pikachu, L50', condition: '100/100', active: true, stats: {atk: 100, def: 100, spa: 120, spd: 100, spe: 120}, moves: ['thunderbolt', 'quickattack'], baseAbility: 'static', ability: 'static', item: 'lightball', pokeball: 'pokeball'},
		{ident: 'p1: Charizard', details: 'Charizard, L50', condition: '100/100', active: false, stats: {atk: 100, def: 100, spa: 120, spd: 100, spe: 100}, moves: ['flamethrower'], baseAbility: 'blaze', ability: 'blaze', item: '', pokeball: 'pokeball'},
	];
	window.PS.receive([`>${roomid}`, '|init|battle', '|title|Alice vs. Bob', '|gametype|singles', '|player|p1|Alice|1|', '|player|p2|Bob|2|', '|teamsize|p1|2', '|teamsize|p2|2', '|gen|9', '|tier|[Gen 9] Custom Game', '|start', '|switch|p1a: Pikachu|Pikachu, L50|100/100', '|switch|p2a: Eevee|Eevee, L50|100/100', '|turn|1'].join('\n'));
	window.PS.focusRoom(roomid);
	const room = window.PS.rooms[roomid];
	room.width = 1000;
	room.height = 800;
	room.update(null);
	window.PS.update();
	return roomid;
}
function deliverRequest(roomid) {
	const request = {active: [{moves: [
		{move: 'Thunderbolt', id: 'thunderbolt', pp: 24, maxpp: 24, target: 'normal', disabled: false},
		{move: 'Quick Attack', id: 'quickattack', pp: 48, maxpp: 48, target: 'normal', disabled: false},
	], canTerastallize: 'Electric'}], side: {name: 'Alice', id: 'p1', pokemon: window.__battleChromePokemon}, rqid: 1};
	const room = window.PS.rooms[roomid];
	room.receiveLine(['request', JSON.stringify(request)]);
	room.battle.seekTurn(Infinity);
	room.update(null);
	window.PS.update();
	return true;
}
function inspectMove(roomid) {
	const root = document.querySelector(`#room-${roomid}`);
	const move = root?.querySelector('button[data-cmd="/movemenu"]');
	const sw = root?.querySelector('button[data-cmd="/switchmenu"]');
	if (!move || !sw) throw new Error('Battle/Switch overlay buttons missing');
	if (move.textContent.trim() !== '対戦' || sw.textContent.trim() !== '交代') throw new Error(`Japanese battle tabs missing: ${root.textContent}`);
	window.__battleChromeClick(`#room-${roomid} button[data-cmd="/movemenu"]`);
	if (window.PS.rooms[roomid].overlayActive !== 'move') throw new Error('Move menu command did not activate');
	window.__battleChromeClick(`#room-${roomid} button[data-cmd="/switchmenu"]`);
	if (window.PS.rooms[roomid].overlayActive !== 'switch') throw new Error('Switch menu command did not activate');
	return {battle: move.textContent.trim(), switch: sw.textContent.trim(), commands: [move.dataset.cmd, sw.dataset.cmd]};
}
async function showTeamPreview(roomid) {
	const room = window.PS.rooms[roomid];
	const request = {teamPreview: true, maxTeamSize: 2, side: room.request.side, rqid: 2};
	room.receiveLine(['request', JSON.stringify(request)]);
	await new Promise(resolve => setTimeout(resolve, 250));
	const root = document.querySelector(`#room-${roomid}`);
	if (!root.textContent.includes('チーム') || !root.textContent.includes('先発を選択')) throw new Error(`Japanese team preview missing: ${root.textContent}`);
	window.__battleChromeClick(`#room-${roomid} button[data-cmd="/switch 1"]`);
	await new Promise(resolve => setTimeout(resolve, 250));
	if (!root.textContent.includes('現在の選出')) throw new Error(`Chosen-team heading missing: ${root.textContent}`);
	const beforeCancel = room.choices.alreadySwitchingIn.length;
	window.__battleChromeClick(`#room-${roomid} button[data-cmd="/cancel"]`);
	return {beforeCancel, afterCancel: room.choices.alreadySwitchingIn.length, text: root.textContent.trim()};
}
async function finishBattle(roomid) {
	window.PS.receive(`>${roomid}\n|win|Alice`);
	const room = window.PS.rooms[roomid];
	room.battle.seekTurn(Infinity);
	room.update(null);
	window.PS.update();
	await new Promise(resolve => setTimeout(resolve, 250));
	const root = document.querySelector(`#room-${roomid}`);
	if (!root.textContent.includes('メインメニュー') || !root.textContent.includes('再戦')) throw new Error(`Japanese post-battle controls missing: ${root.textContent}`);
	return root.textContent.trim();
}
async function inspectBattleList() {
	window.PS.join('battles');
	window.PS.focusRoom('battles');
	await new Promise(resolve => setTimeout(resolve, 250));
	const root = document.querySelector('#room-battles');
	const input = root?.querySelector('input[name="prefixsearch"]');
	const search = root?.querySelector('button[type="submit"]');
	if (input?.placeholder !== 'ユーザー名（前方一致）' || search?.textContent.trim() !== '検索') throw new Error(`Japanese spectator search missing: ${input?.placeholder} / ${search?.textContent}`);
	return {placeholder: input.placeholder, button: search.textContent.trim()};
}
fs.mkdirSync(args.outputDir, {recursive: true});
const client = new CDP((await findPageTarget()).webSocketDebuggerUrl);
await client.connect();
try {
	await client.send('Page.enable');
	await client.send('Runtime.enable');
	await client.send('Emulation.setDeviceMetricsOverride', {width: 1280, height: 900, deviceScaleFactor: 1, mobile: false});
	await client.send('Page.navigate', {url: args.url});
	await wait(client, 'Boolean(window.PS && window.PS.roomTypes && window.PS.roomTypes.battle)', 'client battle modules');
	await call(client, installBrowserHelpers);
	const roomid = await call(client, seedBattle);
	await wait(client, `Boolean(window.PS.rooms['${roomid}']?.battle)`, 'battle model');
	await call(client, deliverRequest, roomid);
	await wait(client, `Boolean(document.querySelector('#room-${roomid} button[data-cmd="/movemenu"]') && document.querySelector('#room-${roomid} button[data-cmd="/switchmenu"]'))`, 'battle overlay controls');
	const move = await call(client, inspectMove, roomid);
	await screenshot(client, 'japanese-battle-move-controls.png');
	const team = await call(client, showTeamPreview, roomid);
	await screenshot(client, 'japanese-battle-team-preview.png');
	const postBattle = await call(client, finishBattle, roomid);
	await screenshot(client, 'japanese-battle-post-battle.png');
	const battleList = await call(client, inspectBattleList);
	const report = {verified: true, roomid, move, team, postBattle, battleList, sent: await evaluate(client, 'window.__battleChromeSent')};
	fs.writeFileSync(path.join(args.outputDir, 'japanese-battle-chrome-report.json'), JSON.stringify(report, null, 2) + '\n');
} finally {
	client.close();
}
