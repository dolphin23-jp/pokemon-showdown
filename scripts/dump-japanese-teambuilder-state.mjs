#!/usr/bin/env node

import fs from 'node:fs';

const debugUrl = process.argv[2] || 'http://127.0.0.1:9222';
const outputPath = process.argv[3] || '/tmp/japanese-teambuilder-browser-state.json';

const targetsResponse = await fetch(`${debugUrl}/json`);
if (!targetsResponse.ok) throw new Error(`Chrome target query failed: ${targetsResponse.status}`);
const targets = await targetsResponse.json();
const page = targets.find(target => target.type === 'page' && target.webSocketDebuggerUrl);
if (!page) throw new Error('Chrome page target not found');

const socket = new WebSocket(page.webSocketDebuggerUrl);
let nextId = 1;
const pending = new Map();

socket.addEventListener('message', event => {
	const message = JSON.parse(String(event.data));
	if (!message.id) return;
	const request = pending.get(message.id);
	if (!request) return;
	pending.delete(message.id);
	if (message.error) request.reject(new Error(message.error.message));
	else request.resolve(message.result || {});
});

await new Promise((resolve, reject) => {
	const timer = setTimeout(() => reject(new Error('Timed out connecting to Chrome')), 10_000);
	socket.addEventListener('open', () => {
		clearTimeout(timer);
		resolve();
	}, { once: true });
	socket.addEventListener('error', () => {
		clearTimeout(timer);
		reject(new Error('Chrome WebSocket error'));
	}, { once: true });
});

const send = (method, params = {}) => {
	const id = nextId++;
	return new Promise((resolve, reject) => {
		pending.set(id, { resolve, reject });
		socket.send(JSON.stringify({ id, method, params }));
	});
};

try {
	const expression = `(() => {
		const summarize = element => element ? {
			connected: element.isConnected,
			dataEntry: element.getAttribute?.('data-entry') || null,
			focus: element.getAttribute?.('data-focus') || null,
			name: element.getAttribute?.('name') || null,
			value: 'value' in element ? element.value : null,
			text: element.textContent?.trim() || '',
			nameText: element.querySelector?.('.movenamecol, .pokemonnamecol, .namecol')?.textContent?.trim() || '',
			outerHTML: element.outerHTML?.slice(0, 1200) || '',
		} : null;
		const editor = window.PS?.room?.editor;
		const search = editor?.search;
		const exactMove = document.querySelector('a[data-entry^="move|Thunderbolt"]');
		return {
			url: location.href,
			documentReadyState: document.readyState,
			displayNameAPI: {
				thunderbolt: window.PSDisplayNames?.displayMoveName?.('Thunderbolt') || null,
				pikachu: window.PSDisplayNames?.displaySpeciesName?.('Pikachu') || null,
				static: window.PSDisplayNames?.displayAbilityName?.('Static') || null,
				lightBall: window.PSDisplayNames?.displayItemName?.('Light Ball') || null,
			},
			generatedTable: {
				thunderbolt: window.BattleJapaneseDisplayNames?.moves?.thunderbolt || null,
			},
			room: {
				id: window.PS?.room?.id || null,
				innerFocusType: editor?.innerFocus?.type || null,
				searchQuery: search?.query || null,
				searchSelection: search?.selection ?? null,
				searchResultCount: search?.results?.length ?? null,
				searchResults: (search?.results || []).slice(0, 20),
				set: editor?.sets?.[0] || null,
			},
			activeElement: summarize(document.activeElement),
			exactThunderbolt: summarize(exactMove),
			moveRows: [...document.querySelectorAll('a[data-entry^="move|"]')].slice(0, 30).map(summarize),
			allSetFields: [...document.querySelectorAll('input.set-field')].map(summarize),
			focusEditorHTML: document.querySelector('.team-focus-editor')?.outerHTML?.slice(0, 12000) || null,
		};
	})()`;
	const response = await send('Runtime.evaluate', {
		expression,
		returnByValue: true,
		awaitPromise: true,
	});
	if (response.exceptionDetails) {
		throw new Error(response.exceptionDetails.exception?.description || response.exceptionDetails.text);
	}
	fs.writeFileSync(outputPath, JSON.stringify(response.result?.value || null, null, 2) + '\n');
	console.log(fs.readFileSync(outputPath, 'utf8'));
} finally {
	socket.close();
}
