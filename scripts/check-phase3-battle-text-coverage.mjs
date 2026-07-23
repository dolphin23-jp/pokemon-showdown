#!/usr/bin/env node

import {spawnSync} from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const SCRIPT_PATH = fileURLToPath(import.meta.url);
const DEFAULT_SERVER_ROOT = path.resolve(path.dirname(SCRIPT_PATH), '..');

function usage() {
	console.log(`Usage: node scripts/check-phase3-battle-text-coverage.mjs [options]

Options:
  --server-root <path>  Server repository root (default: repository containing this script)
  --client-root <path>  Client repository root (forwarded to the inventory generator)
  --help                Show this help
`);
}

function parseArgs(argv) {
	const args = {serverRoot: DEFAULT_SERVER_ROOT, clientRoot: ''};
	for (let index = 0; index < argv.length; index++) {
		const arg = argv[index];
		if (arg === '--help') {
			usage();
			process.exit(0);
		}
		if (!['--server-root', '--client-root'].includes(arg)) {
			throw new Error(`Unknown argument: ${arg}`);
		}
		const value = argv[++index];
		if (!value) throw new Error(`${arg} requires a value`);
		if (arg === '--server-root') args.serverRoot = value;
		if (arg === '--client-root') args.clientRoot = value;
	}
	args.serverRoot = path.resolve(args.serverRoot);
	args.clientRoot = args.clientRoot ? path.resolve(args.clientRoot) : '';
	return args;
}

function runGenerator(args, outputPath) {
	const generatorPath = path.join(args.serverRoot, 'scripts/generate-phase3-battle-text-inventory.mjs');
	if (!fs.existsSync(generatorPath)) throw new Error(`Inventory generator not found: ${generatorPath}`);
	const generatorArgs = [
		generatorPath,
		'--server-root', args.serverRoot,
		'--output', outputPath,
	];
	if (args.clientRoot) generatorArgs.push('--client-root', args.clientRoot);
	const result = spawnSync(process.execPath, generatorArgs, {
		encoding: 'utf8',
		stdio: ['ignore', 'pipe', 'pipe'],
	});
	if (result.stdout) process.stdout.write(result.stdout);
	if (result.stderr) process.stderr.write(result.stderr);
	if (result.status !== 0) {
		throw new Error(`BattleText inventory generator failed with exit code ${result.status}`);
	}
}

function checkInventory(inventory) {
	if (!Number.isInteger(inventory.totalMissing) || inventory.totalMissing < 0) {
		throw new Error(`Invalid totalMissing value: ${inventory.totalMissing}`);
	}
	if (!inventory.byNamespace || typeof inventory.byNamespace !== 'object' || Array.isArray(inventory.byNamespace)) {
		throw new Error('Invalid byNamespace value in generated BattleText inventory');
	}
	const namespaces = Object.keys(inventory.byNamespace);
	if (inventory.totalMissing !== 0 || namespaces.length !== 0) {
		const summary = namespaces.map(namespace => (
			`${namespace}: ${inventory.byNamespace[namespace].join(', ')}`
		)).join('; ');
		throw new Error(
			`Phase 3 BattleText coverage regressed: totalMissing: ${inventory.totalMissing}` +
			(summary ? ` (${summary})` : '')
		);
	}
	console.log(JSON.stringify({
		check: 'phase3-battle-text-coverage',
		generatedFromServerSha: inventory.generatedFromServerSha,
		generatedFromClientSha: inventory.generatedFromClientSha,
		totalMissing: inventory.totalMissing,
		byNamespace: inventory.byNamespace,
	}));
}

function main() {
	const args = parseArgs(process.argv.slice(2));
	const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'phase3-battle-text-coverage-'));
	const outputPath = path.join(tempRoot, 'inventory.json');
	try {
		runGenerator(args, outputPath);
		checkInventory(JSON.parse(fs.readFileSync(outputPath, 'utf8')));
	} finally {
		fs.rmSync(tempRoot, {recursive: true, force: true});
	}
}

try {
	main();
} catch (error) {
	console.error(error instanceof Error ? error.stack : error);
	process.exit(1);
}
