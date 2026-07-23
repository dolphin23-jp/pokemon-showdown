#!/usr/bin/env node

import {execFileSync, spawnSync} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import ts from 'typescript';

const SCRIPT_PATH = fileURLToPath(import.meta.url);
const DEFAULT_SERVER_ROOT = path.resolve(path.dirname(SCRIPT_PATH), '..');
const SERVER_TEXT_FILES = [
	'data/text/default.ts',
	'data/text/moves.ts',
	'data/text/abilities.ts',
	'data/text/items.ts',
];
const RELEVANT_SERVER_PATHS = [
	...SERVER_TEXT_FILES,
	'scripts/generate-phase3-battle-text-inventory.mjs',
];
const DESCRIPTION_KEY = /^(?:desc|shortDesc)(?:Gen\d)?$/;

function usage() {
	console.log(`Usage: node scripts/generate-phase3-battle-text-inventory.mjs [options]

Options:
  --server-root <path>  Server repository root (default: repository containing this script)
  --client-root <path>  Client repository root (default: env/sibling/cache discovery)
  --output <path>       Output JSON path (default: docs/localization/phase-3-battle-text-inventory.json)
  --check               Verify the committed output instead of rewriting it
  --help                Show this help
`);
}

function parseArgs(argv) {
	const args = {
		serverRoot: DEFAULT_SERVER_ROOT,
		clientRoot: '',
		output: '',
		check: false,
	};
	for (let i = 0; i < argv.length; i++) {
		const arg = argv[i];
		if (arg === '--help') {
			usage();
			process.exit(0);
		} else if (arg === '--check') {
			args.check = true;
		} else if (['--server-root', '--client-root', '--output'].includes(arg)) {
			const value = argv[++i];
			if (!value) throw new Error(`${arg} requires a value`);
			if (arg === '--server-root') args.serverRoot = value;
			if (arg === '--client-root') args.clientRoot = value;
			if (arg === '--output') args.output = value;
		} else {
			throw new Error(`Unknown argument: ${arg}`);
		}
	}
	args.serverRoot = path.resolve(args.serverRoot);
	args.clientRoot = args.clientRoot ? path.resolve(args.clientRoot) : '';
	args.output = path.resolve(
		args.output || path.join(args.serverRoot, 'docs/localization/phase-3-battle-text-inventory.json')
	);
	return args;
}

function readJSON(filePath) {
	return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function git(root, args, options = {}) {
	return execFileSync('git', ['-C', root, ...args], {
		encoding: 'utf8',
		stdio: options.stdio || ['ignore', 'pipe', 'pipe'],
	}).trim();
}

function gitHead(root) {
	const sha = git(root, ['rev-parse', 'HEAD']);
	if (!/^[0-9a-f]{40}$/.test(sha)) throw new Error(`Invalid Git HEAD for ${root}: ${sha}`);
	return sha;
}

function resolveClientRoot(serverRoot, explicitRoot) {
	const candidates = [
		explicitRoot,
		process.env.POKEMON_SHOWDOWN_CLIENT_ROOT,
		path.resolve(serverRoot, '..', 'pokemon-showdown-client'),
		path.resolve(serverRoot, 'caches', 'pokemon-showdown-client'),
	].filter(Boolean).map(candidate => path.resolve(candidate));
	for (const candidate of candidates) {
		if (fs.existsSync(path.join(candidate, 'play.pokemonshowdown.com/src/battle-text-ja.js'))) {
			return candidate;
		}
	}
	throw new Error([
		'Unable to locate pokemon-showdown-client.',
		'Pass --client-root or set POKEMON_SHOWDOWN_CLIENT_ROOT.',
		`Checked: ${candidates.join(', ')}`,
	].join(' '));
}

function parseSource(filePath, scriptKind) {
	const source = fs.readFileSync(filePath, 'utf8');
	return ts.createSourceFile(filePath, source, ts.ScriptTarget.Latest, true, scriptKind);
}

function findObjectDeclaration(sourceFile, variableName) {
	let found = null;
	function visit(node) {
		if (found) return;
		if (ts.isVariableDeclaration(node) && ts.isIdentifier(node.name) && node.name.text === variableName) {
			if (!node.initializer || !ts.isObjectLiteralExpression(node.initializer)) {
				throw new Error(`${variableName} in ${sourceFile.fileName} is not initialized with an object literal`);
			}
			found = node.initializer;
			return;
		}
		ts.forEachChild(node, visit);
	}
	visit(sourceFile);
	if (!found) throw new Error(`Could not find ${variableName} in ${sourceFile.fileName}`);
	return found;
}

function propertyName(name, sourceFile) {
	if (ts.isIdentifier(name) || ts.isPrivateIdentifier(name)) return name.text;
	if (ts.isStringLiteral(name) || ts.isNumericLiteral(name) || ts.isNoSubstitutionTemplateLiteral(name)) {
		return name.text;
	}
	if (ts.isComputedPropertyName(name) && (
		ts.isStringLiteral(name.expression) || ts.isNoSubstitutionTemplateLiteral(name.expression)
	)) {
		return name.expression.text;
	}
	throw new Error(`Unsupported property name in ${sourceFile.fileName}: ${name.getText(sourceFile)}`);
}

function objectShape(node, sourceFile) {
	const result = new Map();
	for (const property of node.properties) {
		if (ts.isPropertyAssignment(property)) {
			const key = propertyName(property.name, sourceFile);
			result.set(key, ts.isObjectLiteralExpression(property.initializer) ?
				objectShape(property.initializer, sourceFile) : null);
			continue;
		}
		if (ts.isShorthandPropertyAssignment(property)) {
			result.set(property.name.text, null);
			continue;
		}
		throw new Error(`Unsupported object member in ${sourceFile.fileName}: ${property.getText(sourceFile)}`);
	}
	return result;
}

function loadShape(filePath, variableName, scriptKind) {
	const sourceFile = parseSource(filePath, scriptKind);
	return objectShape(findObjectDeclaration(sourceFile, variableName), sourceFile);
}

function cloneNamespaces(source) {
	const result = new Map();
	for (const [namespace, fields] of source) {
		if (!(fields instanceof Map)) throw new Error(`Namespace ${namespace} is not an object`);
		result.set(namespace, new Set(fields.keys()));
	}
	return result;
}

function assignData(text, id, entry) {
	let textEntry = text.get(id);
	if (!textEntry) {
		textEntry = new Set();
		text.set(id, textEntry);
	}
	for (const [key, nested] of entry) {
		if (['name', 'desc', 'shortDesc'].includes(key)) continue;
		if (key.startsWith('gen')) {
			if (!(nested instanceof Map)) throw new Error(`${id}.${key} is not an object`);
			for (const modKey of nested.keys()) {
				// Intentionally reproduce build-tools/build-indexes exactly: this condition
				// checks `key` (for example "gen4"), so it never excludes desc/shortDesc.
				if (['desc', 'shortDesc'].includes(key)) continue;
				textEntry.add(`${modKey}Gen${key.charAt(3)}`);
			}
		} else if (!(nested instanceof Map)) {
			textEntry.add(key);
		}
	}
}

function buildEnglishBattleText(serverRoot) {
	const defaultShape = loadShape(
		path.join(serverRoot, 'data/text/default.ts'), 'DefaultText', ts.ScriptKind.TS
	);
	const text = cloneNamespaces(defaultShape);
	const sources = [
		['data/text/moves.ts', 'MovesText'],
		['data/text/abilities.ts', 'AbilitiesText'],
		['data/text/items.ts', 'ItemsText'],
	];
	for (const [relativePath, variableName] of sources) {
		const data = loadShape(path.join(serverRoot, relativePath), variableName, ts.ScriptKind.TS);
		for (const [id, entry] of data) {
			if (!(entry instanceof Map)) throw new Error(`${variableName}.${id} is not an object`);
			assignData(text, id, entry);
		}
	}
	return text;
}

function buildJapaneseBattleText(clientRoot) {
	const shape = loadShape(
		path.join(clientRoot, 'play.pokemonshowdown.com/src/battle-text-ja.js'),
		'JAPANESE_BATTLE_TEXT',
		ts.ScriptKind.JS
	);
	return cloneNamespaces(shape);
}

function createInventory(serverRoot, clientRoot) {
	const english = buildEnglishBattleText(serverRoot);
	const japanese = buildJapaneseBattleText(clientRoot);
	const byNamespace = {};
	let totalMissing = 0;
	for (const namespace of [...english.keys()].sort()) {
		const translatedKeys = japanese.get(namespace) || new Set();
		const missing = [...english.get(namespace)]
			.filter(key => !DESCRIPTION_KEY.test(key) && !translatedKeys.has(key))
			.sort();
		if (!missing.length) continue;
		byNamespace[namespace] = missing;
		totalMissing += missing.length;
	}
	return {
		generatedFromServerSha: gitHead(serverRoot),
		generatedFromClientSha: gitHead(clientRoot),
		totalMissing,
		byNamespace,
	};
}

function assertPinnedClient(serverRoot, clientRoot, inventory) {
	const pin = readJSON(path.join(serverRoot, 'config/pokemon-showdown-client.json'));
	if (inventory.generatedFromClientSha !== pin.commit) {
		throw new Error(
			`Client HEAD ${inventory.generatedFromClientSha} does not match pinned commit ${pin.commit}`
		);
	}
	const expectedRemote = `github.com/${pin.fork_repository}`;
	try {
		const remote = git(clientRoot, ['remote', 'get-url', 'origin']);
		if (!remote.includes(expectedRemote) && !remote.includes(`${pin.fork_repository}.git`)) {
			throw new Error(`Client origin ${remote} does not match ${pin.fork_repository}`);
		}
	} catch (error) {
		if (error instanceof Error && error.message.startsWith('Client origin')) throw error;
		// A detached archive can lack an origin; the exact pinned SHA check remains authoritative.
	}
}

function relevantInputsUnchanged(serverRoot, baselineSha) {
	const ancestor = spawnSync('git', ['-C', serverRoot, 'merge-base', '--is-ancestor', baselineSha, 'HEAD']);
	if (ancestor.status !== 0) {
		throw new Error(`Recorded server SHA ${baselineSha} is not an ancestor of HEAD`);
	}
	const diff = spawnSync('git', [
		'-C', serverRoot, 'diff', '--quiet', `${baselineSha}..HEAD`, '--', ...RELEVANT_SERVER_PATHS,
	]);
	if (diff.status !== 0) {
		throw new Error(`BattleText inventory inputs changed after recorded server SHA ${baselineSha}`);
	}
}

function stableJSON(value) {
	return `${JSON.stringify(value, null, 2)}\n`;
}

function checkCommittedOutput(args, generated) {
	if (!fs.existsSync(args.output)) throw new Error(`Committed inventory is missing: ${args.output}`);
	const committed = readJSON(args.output);
	if (!/^[0-9a-f]{40}$/.test(committed.generatedFromServerSha || '')) {
		throw new Error('Committed generatedFromServerSha is invalid');
	}
	if (committed.generatedFromClientSha !== generated.generatedFromClientSha) {
		throw new Error('Committed generatedFromClientSha does not match the pinned client checkout');
	}
	relevantInputsUnchanged(args.serverRoot, committed.generatedFromServerSha);
	const comparableGenerated = {...generated, generatedFromServerSha: committed.generatedFromServerSha};
	if (stableJSON(committed) !== stableJSON(comparableGenerated)) {
		throw new Error(`Committed inventory is stale. Regenerate ${path.relative(args.serverRoot, args.output)}`);
	}
	console.log(`Verified ${path.relative(args.serverRoot, args.output)} (${committed.totalMissing} missing keys).`);
}

function main() {
	const args = parseArgs(process.argv.slice(2));
	const clientRoot = resolveClientRoot(args.serverRoot, args.clientRoot);
	for (const relativePath of SERVER_TEXT_FILES) {
		if (!fs.existsSync(path.join(args.serverRoot, relativePath))) {
			throw new Error(`Missing server input: ${relativePath}`);
		}
	}
	const inventory = createInventory(args.serverRoot, clientRoot);
	assertPinnedClient(args.serverRoot, clientRoot, inventory);
	if (args.check) {
		checkCommittedOutput(args, inventory);
		return;
	}
	fs.mkdirSync(path.dirname(args.output), {recursive: true});
	fs.writeFileSync(args.output, stableJSON(inventory));
	console.log(`Wrote ${path.relative(args.serverRoot, args.output)} (${inventory.totalMissing} missing keys).`);
}

try {
	main();
} catch (error) {
	console.error(error instanceof Error ? error.stack : error);
	process.exit(1);
}
