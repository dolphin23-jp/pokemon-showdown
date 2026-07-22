#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';

function parseArgs(argv) {
	const args = {
		debugUrl: 'http://127.0.0.1:9222',
		outputDir: '/tmp/japanese-teambuilder',
		url: 'http://127.0.0.1:10004/index-new.html#teambuilder',
	};
	for (let index = 2; index < argv.length; index++) {
		const argument = argv[index];
		if (argument === '--debug-url') args.debugUrl = argv[++index];
		else if (argument === '--output-dir') args.outputDir = argv[++index];
		else if (argument === '--url') args.url = argv[++index];
		else throw new Error(`Unknown argument: ${argument}`);
	}
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
		if (message.error) {
			pending.reject(new Error(`${pending.method}: ${message.error.message}`));
		} else {
			pending.resolve(message.result || {});
		}
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

async function waitForPage(client, expression, label, timeout = 45_000) {
	const deadline = Date.now() + timeout;
	let lastValue = null;
	while (Date.now() < deadline) {
		lastValue = await evaluate(client, expression);
		if (lastValue) return lastValue;
		await sleep(150);
	}
	throw new Error(`Timed out waiting for ${label}; last value=${JSON.stringify(lastValue)}`);
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

const args = parseArgs(process.argv);
fs.mkdirSync(args.outputDir, { recursive: true });
const reportPath = path.join(args.outputDir, 'japanese-teambuilder-report.json');
const formScreenshotPath = path.join(args.outputDir, 'japanese-teambuilder-form.png');
const exportScreenshotPath = path.join(args.outputDir, 'japanese-teambuilder-import-export.png');

const target = await findPageTarget(args.debugUrl);
const client = new CDPClient(target.webSocketDebuggerUrl);
await client.connect();

const report = {
	url: args.url,
	verified: false,
	form: null,
	importExport: null,
};

try {
	await client.send('Page.enable');
	await client.send('Runtime.enable');
	await client.send('Emulation.setDeviceMetricsOverride', {
		width: 1280,
		height: 900,
		deviceScaleFactor: 1,
		mobile: false,
	});
	await client.send('Page.navigate', { url: args.url });
	await waitForPage(
		client,
		`Boolean(window.PS && document.querySelector('#room-teambuilder'))`,
		'Teambuilder landing page'
	);

	await evaluate(client, `(() => {
		localStorage.removeItem('showdown_teams');
		return true;
	})()`);
	await client.send('Page.reload', { ignoreCache: true });
	await sleep(750);
	await waitForPage(
		client,
		`Boolean(window.PS && document.querySelector('#room-teambuilder button[data-cmd="/newteam"]'))`,
		'empty Teambuilder after storage reset'
	);

	const formReport = await evaluate(client, `(async () => {
		const delay = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));
		const waitFor = async (predicate, label, timeout = 30_000) => {
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
			throw new Error('Timed out waiting for ' + label + (lastError ? ': ' + lastError.message : ''));
		};
		const click = element => {
			if (!element) throw new Error('Attempted to click a missing element');
			element.scrollIntoView({ block: 'center', inline: 'center' });
			element.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, button: 0 }));
			element.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, button: 0 }));
			element.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 }));
		};
		const setInputValue = (input, value) => {
			const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
			setter.call(input, value);
			input.dispatchEvent(new Event('input', { bubbles: true, composed: true }));
		};
		const canonicalModelMatches = (focus, expectedCanonical) => {
			const set = window.PS?.room?.editor?.sets?.[0];
			if (!set) return false;
			if (focus.endsWith('-pokemon')) return set.species === expectedCanonical;
			if (focus.endsWith('-ability')) return set.ability === expectedCanonical;
			if (focus.endsWith('-item')) return set.item === expectedCanonical;
			if (focus.endsWith('-move-0')) return set.moves?.[0] === expectedCanonical;
			return false;
		};
		const choose = async (focus, query, expectedCanonical, entrySelector) => {
			let input = await waitFor(
				() => document.querySelector('.team-focus-editor input.set-field[data-focus="' + focus + '"]') ||
					document.querySelector('.teameditor input.set-field[data-focus="' + focus + '"]'),
				focus + ' input'
			);
			input.focus();
			await delay(120);
			input = document.querySelector('.team-focus-editor input.set-field[data-focus="' + focus + '"]') || input;
			setInputValue(input, query);
			const result = await waitFor(
				() => document.querySelector(entrySelector),
				entrySelector + ' result'
			);
			result.addEventListener('click', event => event.preventDefault(), { once: true });
			click(result);
			await waitFor(
				() => canonicalModelMatches(focus, expectedCanonical),
				focus + ' canonical model value'
			);
			await delay(150);
		};

		click(document.querySelector('#room-teambuilder button[data-cmd="/newteam"]'));
		const teamLink = await waitFor(
			() => document.querySelector('#room-teambuilder a.team[href^="team-"]'),
			'new team link'
		);
		click(teamLink);
		await waitFor(
			() => window.PS?.room?.editor && document.querySelector('.teameditor'),
			'new team editor'
		);
		click(await waitFor(
			() => document.querySelector('.teameditor button[name="addpokemon"]'),
			'Add Pokemon button'
		));
		await choose('set-0-pokemon', 'Pikachu', 'Pikachu', 'a[data-entry^="pokemon|Pikachu"]');
		await choose('set-0-ability', 'Static', 'Static', 'a[data-entry^="ability|Static"]');
		await choose('set-0-item', 'Light Ball', 'Light Ball', 'a[data-entry^="item|Light Ball"]');
		await choose('set-0-move-0', 'Thunderbolt', 'Thunderbolt', 'a[data-entry^="move|Thunderbolt"]');

		const backButton = document.querySelector('.team-focus-editor .tabbar .home-li button');
		if (backButton) click(backButton);
		await waitFor(() => !document.querySelector('.team-focus-editor'), 'closed focused editor');
		document.activeElement?.blur?.();
		await delay(350);

		const field = focus => document.querySelector('.teameditor input.set-field[data-focus="' + focus + '"]');
		const values = {
			species: field('set-0-pokemon')?.value || '',
			ability: field('set-0-ability')?.value || '',
			item: field('set-0-item')?.value || '',
			move: field('set-0-move-0')?.value || '',
		};
		const canonical = {
			species: field('set-0-pokemon')?.getAttribute('data-ps-canonical-value') || '',
			ability: field('set-0-ability')?.getAttribute('data-ps-canonical-value') || '',
			item: field('set-0-item')?.getAttribute('data-ps-canonical-value') || '',
			move: field('set-0-move-0')?.getAttribute('data-ps-canonical-value') || '',
		};
		const set = window.PS.room.editor.sets[0];
		const model = {
			species: set.species,
			ability: set.ability,
			item: set.item,
			moves: [...set.moves],
			packedTeam: window.PS.room.team.packedTeam,
		};
		const formButton = document.querySelector('.teameditor > .tabbar button[value="form"]');
		const importButton = document.querySelector('.teameditor > .tabbar button[value="import"]');
		const detailsButton = document.querySelector('.teameditor button[name="details"][value="set-0-details"]');
		const fixedText = {
			formTab: formButton?.textContent.trim() || '',
			importExport: importButton?.textContent.trim() || '',
			details: detailsButton?.closest('label')?.childNodes?.[0]?.nodeValue?.trim() || '',
		};
		const expectedValues = {
			species: 'ピカチュウ',
			ability: 'せいでんき',
			item: 'でんきだま',
			move: '10まんボルト',
		};
		const expectedCanonical = {
			species: 'Pikachu',
			ability: 'Static',
			item: 'Light Ball',
			move: 'Thunderbolt',
		};
		if (JSON.stringify(values) !== JSON.stringify(expectedValues)) {
			throw new Error('Japanese form values mismatch: ' + JSON.stringify(values));
		}
		if (JSON.stringify(canonical) !== JSON.stringify(expectedCanonical)) {
			throw new Error('Canonical DOM values mismatch: ' + JSON.stringify(canonical));
		}
		if (
			model.species !== 'Pikachu' || model.ability !== 'Static' ||
			model.item !== 'Light Ball' || model.moves[0] !== 'Thunderbolt'
		) {
			throw new Error('Canonical editor model mismatch: ' + JSON.stringify(model));
		}
		if (/[\\u3040-\\u30ff\\u3400-\\u9fff\\uff66-\\uff9f]/.test(model.packedTeam)) {
			throw new Error('Packed team unexpectedly contains Japanese: ' + model.packedTeam);
		}
		if (
			fixedText.formTab !== 'フォーム' ||
			fixedText.importExport !== 'インポート／エクスポート' ||
			fixedText.details !== '詳細'
		) {
			throw new Error('Fixed Teambuilder text mismatch: ' + JSON.stringify(fixedText));
		}
		return { values, canonical, model, fixedText, roomId: window.PS.room.id };
	})()`);
	report.form = formReport;
	await captureScreenshot(client, formScreenshotPath);

	const importExportReport = await evaluate(client, `(async () => {
		const delay = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));
		const waitFor = async (predicate, label, timeout = 15_000) => {
			const deadline = Date.now() + timeout;
			while (Date.now() < deadline) {
				const value = predicate();
				if (value) return value;
				await delay(100);
			}
			throw new Error('Timed out waiting for ' + label);
		};
		const button = document.querySelector('.teameditor > .tabbar button[value="import"]');
		if (!button) throw new Error('Import/Export tab missing');
		button.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 }));
		const textarea = await waitFor(
			() => document.querySelector('.teameditor textarea.teamtextbox'),
			'Import/Export textarea'
		);
		await delay(250);
		const text = textarea.value;
		const required = ['Pikachu @ Light Ball', 'Ability: Static', '- Thunderbolt'];
		const missing = required.filter(value => !text.includes(value));
		const containsJapanese = /[\\u3040-\\u30ff\\u3400-\\u9fff\\uff66-\\uff9f]/.test(text);
		if (missing.length) throw new Error('Import/Export missing canonical text: ' + JSON.stringify(missing));
		if (containsJapanese) throw new Error('Import/Export unexpectedly contains Japanese: ' + text);
		return { text, required, missing, containsJapanese };
	})()`);
	report.importExport = importExportReport;
	await captureScreenshot(client, exportScreenshotPath);

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
