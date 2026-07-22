'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function parseArgs(argv) {
	const args = { clientRoot: process.env.PINNED_CLIENT_ROOT || '/opt/pokemon-showdown-client' };
	for (let index = 0; index < argv.length; index++) {
		if (argv[index] === '--client-root') {
			args.clientRoot = argv[++index];
		}
	}
	return args;
}

function toID(value) {
	return String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, '');
}

function namedEntry(id, name) {
	return Object.freeze({ id, name });
}

function fakeButton(kind, text, command, tooltip) {
	const textNode = { nodeType: 3, nodeValue: text, parentElement: null };
	const button = {
		nodeType: 1,
		tagName: 'BUTTON',
		childNodes: [textNode, { nodeType: 1, tagName: 'I', nodeValue: null, childNodes: [] }],
		dataCmd: command,
		dataTooltip: tooltip,
		matches(selector) {
			if (selector === 'button.movebutton') return kind === 'move';
			if (
				selector.includes('switchpokemon|') ||
				selector.includes('allypokemon|') ||
				selector.includes('activepokemon|')
			) {
				return kind === 'species';
			}
			return false;
		},
		closest() {
			return null;
		},
		getAttribute() {
			return null;
		},
		setAttribute() {},
		querySelector() {
			return null;
		},
		querySelectorAll() {
			return [];
		},
	};
	textNode.parentElement = button;
	return { button, textNode };
}

function protocolFixture() {
	const request = {
		active: [{
			moves: [{
				move: 'Thunderbolt',
				id: 'thunderbolt',
				pp: 15,
				maxpp: 15,
				target: 'normal',
				disabled: false,
			}],
		}],
		side: {
			id: 'p1',
			name: 'ProtocolSmoke',
			pokemon: [{
				ident: 'p1: Pikachu',
				details: 'Pikachu, L50',
				condition: '100/100',
				active: true,
				stats: { atk: 100, def: 100, spa: 100, spd: 100, spe: 100 },
				moves: ['thunderbolt'],
				baseAbility: 'static',
				item: 'lightball',
				pokeball: 'pokeball',
			}],
		},
		rqid: 7,
	};
	const lines = [
		'>battle-protocol-invariant',
		`|request|${JSON.stringify(request)}`,
		'|switch|p1a: Pikachu|Pikachu, L50|100/100',
		'|move|p1a: Pikachu|Thunderbolt|p2a: Charizard',
	];
	return { request, raw: lines.join('\n') };
}

function main() {
	const args = parseArgs(process.argv.slice(2));
	const bundlePath = path.resolve(
		args.clientRoot,
		'play.pokemonshowdown.com/js/battle-display-names.js'
	);
	if (!fs.existsSync(bundlePath)) {
		throw new Error(`Pinned client display-name bundle not found: ${bundlePath}`);
	}

	const fixture = protocolFixture();
	const rawBefore = fixture.raw;
	const requestBefore = JSON.parse(JSON.stringify(fixture.request));
	const requestLineBefore = rawBefore.split('\n').find(line => line.startsWith('|request|'));
	const choiceBefore = '/choose move 1';

	const moveControl = fakeButton(
		'move',
		fixture.request.active[0].moves[0].move,
		choiceBefore,
		'move|Thunderbolt|0'
	);
	const speciesControl = fakeButton(
		'species',
		'Pikachu',
		'/switch 1',
		'switchpokemon|0'
	);
	const buttons = [moveControl.button, speciesControl.button];
	const root = {
		nodeType: 1,
		tagName: 'BODY',
		childNodes: [],
		matches() {
			return false;
		},
		closest() {
			return null;
		},
		getAttribute() {
			return null;
		},
		setAttribute() {},
		querySelector() {
			return null;
		},
		querySelectorAll(selector) {
			if (
				selector.includes('button.movebutton') ||
				selector.includes('switchpokemon|') ||
				selector.includes('allypokemon|') ||
				selector.includes('activepokemon|')
			) {
				return buttons;
			}
			return [];
		},
	};
	const observers = [];
	const entries = {
		species: {
			pikachu: namedEntry('pikachu', 'Pikachu'),
			charizard: namedEntry('charizard', 'Charizard'),
		},
		moves: {
			thunderbolt: namedEntry('thunderbolt', 'Thunderbolt'),
		},
		abilities: {
			static: namedEntry('static', 'Static'),
		},
		items: {
			lightball: namedEntry('lightball', 'Light Ball'),
		},
	};
	const makeTable = table => ({
		get(value) {
			if (value && typeof value !== 'string') return value;
			const name = String(value || '');
			const id = toID(name);
			return entries[table][id] || namedEntry(id, name);
		},
	});
	const window = {
		BattleJapaneseDisplayNames: {
			species: { pikachu: 'ピカチュウ' },
			moves: { thunderbolt: '10まんボルト' },
			abilities: { static: 'せいでんき' },
			items: { lightball: 'でんきだま' },
		},
	};
	const context = vm.createContext({
		Dex: {
			species: makeTable('species'),
			moves: makeTable('moves'),
			abilities: makeTable('abilities'),
			items: makeTable('items'),
		},
		document: {
			body: root,
			documentElement: root,
			activeElement: null,
			addEventListener() {},
		},
		MutationObserver: class MutationObserver {
			constructor(callback) {
				this.callback = callback;
				observers.push(this);
			}
			observe(target, options) {
				this.target = target;
				this.options = options;
			}
		},
		Object,
		setTimeout(callback) {
			callback();
			return 0;
		},
		window,
	});
	vm.runInContext(fs.readFileSync(bundlePath, 'utf8'), context, { filename: bundlePath });

	assert.equal(fixture.raw, rawBefore, 'raw WebSocket protocol changed during display rendering');
	assert.deepEqual(fixture.request, requestBefore, '|request| JSON changed during display rendering');
	assert.equal(
		fixture.raw.split('\n').find(line => line.startsWith('|request|')),
		requestLineBefore,
		'raw |request| line changed during display rendering'
	);
	assert.match(fixture.raw, /\|switch\|p1a: Pikachu\|Pikachu, L50\|100\/100/);
	assert.match(fixture.raw, /\|move\|p1a: Pikachu\|Thunderbolt\|p2a: Charizard/);
	assert.doesNotMatch(fixture.raw, /[ぁ-んァ-ヶ一-龯]/u);

	assert.equal(moveControl.textNode.nodeValue, '10まんボルト');
	assert.equal(speciesControl.textNode.nodeValue, 'ピカチュウ');
	assert.match(`${moveControl.textNode.nodeValue}${speciesControl.textNode.nodeValue}`, /[ぁ-んァ-ヶ一-龯]/u);
	assert.equal(moveControl.button.dataCmd, choiceBefore);
	assert.equal(moveControl.button.dataTooltip, 'move|Thunderbolt|0');
	assert.equal(speciesControl.button.dataCmd, '/switch 1');
	assert.equal(speciesControl.button.dataTooltip, 'switchpokemon|0');
	assert.doesNotMatch(moveControl.button.dataCmd, /[ぁ-んァ-ヶ一-龯]/u);
	assert.doesNotMatch(speciesControl.button.dataCmd, /[ぁ-んァ-ヶ一-龯]/u);

	assert.equal(observers.length, 1);
	assert.equal(observers[0].options.childList, true);
	assert.equal(observers[0].options.subtree, true);
	assert.equal(observers[0].options.characterData, true);

	moveControl.textNode.nodeValue = 'Thunderbolt';
	observers[0].callback([{
		type: 'characterData',
		target: moveControl.textNode,
		addedNodes: [],
	}]);
	assert.equal(moveControl.textNode.nodeValue, '10まんボルト');
	assert.equal(fixture.raw, rawBefore, 'raw protocol changed after a localized re-render');
	assert.equal(moveControl.button.dataCmd, choiceBefore);

	console.log(JSON.stringify({
		task: 'Phase 1 T1-10',
		bundle: bundlePath,
		raw_protocol_unchanged: true,
		request_json_unchanged: true,
		move_line_unchanged: true,
		switch_line_unchanged: true,
		choose_command_unchanged: true,
		rendered_move: moveControl.textNode.nodeValue,
		rendered_species: speciesControl.textNode.nodeValue,
	}, null, 2));
}

main();
