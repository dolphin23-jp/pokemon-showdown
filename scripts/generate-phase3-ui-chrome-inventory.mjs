#!/usr/bin/env node

import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import ts from 'typescript';

const SCRIPT_PATH = fileURLToPath(import.meta.url);
const DEFAULT_SERVER_ROOT = path.resolve(path.dirname(SCRIPT_PATH), '..');
const TARGET_FILES = [
	'play.pokemonshowdown.com/src/panel-battle.tsx',
	'play.pokemonshowdown.com/src/panel-popups.tsx',
	'play.pokemonshowdown.com/src/battle-team-editor.tsx',
	'play.pokemonshowdown.com/src/panel-teambuilder.tsx',
	'play.pokemonshowdown.com/src/panel-teambuilder-team.tsx',
	'play.pokemonshowdown.com/src/panel-teamdropdown.tsx',
];
const REQUIRED_STRINGS = [
	'Battle',
	'Switch',
	'Team',
	'Cancel',
	'Skip animation',
	'Main menu',
	'Rematch',
	'Move to center',
	'Forfeiting makes you lose the battle. Are you sure?',
];

function usage() {
	console.log(`Usage: node scripts/generate-phase3-ui-chrome-inventory.mjs [options]

Options:
  --server-root <path>  Server repository root (default: repository containing this script)
  --client-root <path>  Client repository root (default: env/sibling/cache discovery)
  --output <path>       Output Markdown path (default: docs/localization/phase-3-ui-chrome-inventory.md)
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
		args.output || path.join(args.serverRoot, 'docs/localization/phase-3-ui-chrome-inventory.md')
	);
	return args;
}

function resolveClientRoot(serverRoot, explicitRoot) {
	const candidates = [
		explicitRoot,
		process.env.POKEMON_SHOWDOWN_CLIENT_ROOT,
		path.resolve(serverRoot, '..', 'pokemon-showdown-client'),
		path.resolve(serverRoot, 'caches', 'pokemon-showdown-client'),
	].filter(Boolean).map(candidate => path.resolve(candidate));
	for (const candidate of candidates) {
		if (TARGET_FILES.every(file => fs.existsSync(path.join(candidate, file)))) return candidate;
	}
	throw new Error([
		'Unable to locate pokemon-showdown-client with all Phase 3 UI files.',
		'Pass --client-root or set POKEMON_SHOWDOWN_CLIENT_ROOT.',
		`Checked: ${candidates.join(', ')}`,
	].join(' '));
}

function gitHead(root) {
	const sha = execFileSync('git', ['-C', root, 'rev-parse', 'HEAD'], {encoding: 'utf8'}).trim();
	if (!/^[0-9a-f]{40}$/.test(sha)) throw new Error(`Invalid Git HEAD for ${root}: ${sha}`);
	return sha;
}

function normalizeText(text) {
	return text.replace(/\s+/g, ' ').trim();
}

function hasEnglish(text) {
	return /[A-Za-z]/.test(text.replace(/&(?:[A-Za-z][A-Za-z0-9]+|#\d+|#x[0-9A-Fa-f]+);/g, ''));
}

function staticText(node) {
	if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) return node.text;
	if (ts.isTemplateExpression(node)) {
		let result = node.head.text;
		for (const span of node.templateSpans) result += '${…}' + span.literal.text;
		return result;
	}
	return null;
}

function jsxAttributeName(attribute) {
	return attribute.name.getText();
}

function openingElementHasDataTooltip(openingElement) {
	return openingElement.attributes.properties.some(attribute =>
		ts.isJsxAttribute(attribute) && jsxAttributeName(attribute) === 'data-tooltip'
	);
}

function lineNumber(sourceFile, node) {
	return sourceFile.getLineAndCharacterOfPosition(node.getStart(sourceFile)).line + 1;
}

function collectExpressionStrings(expression, add) {
	const text = staticText(expression);
	if (text !== null) {
		add(expression, text);
		return;
	}
	if (ts.isParenthesizedExpression(expression)) {
		collectExpressionStrings(expression.expression, add);
		return;
	}
	if (ts.isConditionalExpression(expression)) {
		collectExpressionStrings(expression.whenTrue, add);
		collectExpressionStrings(expression.whenFalse, add);
		return;
	}
	if (ts.isBinaryExpression(expression) && [
		ts.SyntaxKind.AmpersandAmpersandToken,
		ts.SyntaxKind.BarBarToken,
		ts.SyntaxKind.QuestionQuestionToken,
	].includes(expression.operatorToken.kind)) {
		collectExpressionStrings(expression.right, add);
		return;
	}
	if (ts.isArrayLiteralExpression(expression)) {
		for (const element of expression.elements) collectExpressionStrings(element, add);
	}
}

function collectNotify(call, sourceFile, addEntry) {
	if (!ts.isPropertyAccessExpression(call.expression) || call.expression.name.text !== 'notify') return;
	const receiver = call.expression.expression.getText(sourceFile);
	if (!/(?:^|\.)room$|\.room\b/.test(receiver)) return;
	const [first, second] = call.arguments;
	if (first && ts.isObjectLiteralExpression(first)) {
		for (const property of first.properties) {
			if (!ts.isPropertyAssignment(property)) continue;
			const key = property.name.getText(sourceFile).replace(/^['"]|['"]$/g, '');
			if (!['title', 'body'].includes(key)) continue;
			const text = staticText(property.initializer);
			if (text !== null) addEntry(property.initializer, 'notify', text);
		}
		return;
	}
	for (const argument of [first, second]) {
		if (!argument) continue;
		const text = staticText(argument);
		if (text !== null) addEntry(argument, 'notify', text);
	}
}

function collectFile(clientRoot, relativePath, fileIndex) {
	const filePath = path.join(clientRoot, relativePath);
	const source = fs.readFileSync(filePath, 'utf8');
	const sourceFile = ts.createSourceFile(filePath, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
	const entries = [];
	const seen = new Set();
	function addEntry(node, type, rawText) {
		const text = normalizeText(rawText);
		if (!text || !hasEnglish(text)) return;
		const line = lineNumber(sourceFile, node);
		const fingerprint = `${line}\0${type}\0${text}`;
		if (seen.has(fingerprint)) return;
		seen.add(fingerprint);
		entries.push({file: relativePath, fileIndex, line, type, text});
	}
	function visit(node) {
		if (ts.isJsxText(node)) {
			addEntry(node, 'label', node.getText(sourceFile));
		} else if (ts.isJsxExpression(node) && node.expression &&
			(ts.isJsxElement(node.parent) || ts.isJsxFragment(node.parent))) {
			collectExpressionStrings(node.expression, (literalNode, text) => addEntry(literalNode, 'label', text));
		} else if (ts.isJsxAttribute(node)) {
			const name = jsxAttributeName(node);
			if (name === 'placeholder' || name === 'title') {
				const openingElement = node.parent.parent;
				if (name === 'title' && openingElementHasDataTooltip(openingElement)) {
					ts.forEachChild(node, visit);
					return;
				}
				if (node.initializer && ts.isStringLiteral(node.initializer)) {
					addEntry(node.initializer, name, node.initializer.text);
				} else if (node.initializer && ts.isJsxExpression(node.initializer) && node.initializer.expression) {
					const text = staticText(node.initializer.expression);
					if (text !== null) addEntry(node.initializer.expression, name, text);
				}
			}
		} else if (ts.isCallExpression(node)) {
			collectNotify(node, sourceFile, addEntry);
		}
		ts.forEachChild(node, visit);
	}
	visit(sourceFile);
	return entries;
}

function escapeCell(text) {
	return text.replace(/\\/g, '\\\\').replace(/\|/g, '\\|').replace(/`/g, '\\`').replace(/\n/g, '<br>');
}

function renderMarkdown(clientSha, entries) {
	const lines = [
		'# Phase 3 UI chrome inventory',
		'',
		`Generated from client SHA \`${clientSha}\`.`,
		'',
		'This inventory contains hard-coded English UI chrome from the Phase 3 battle and Teambuilder scope. It includes JSX labels, placeholders, general title attributes, and `room.notify(...)` title/body text. It excludes `data-cmd`, `data-tooltip`, translated species/move/ability/item names, and Team Import/Export contents.',
		'',
		'| File:line | Type | Current English string |',
		'| --- | --- | --- |',
	];
	for (const entry of entries) {
		lines.push(`| \`${entry.file}:${entry.line}\` | \`${entry.type}\` | ${escapeCell(entry.text)} |`);
	}
	lines.push('');
	return lines.join('\n');
}

function assertRequiredStrings(entries) {
	const texts = new Set(entries.map(entry => entry.text));
	for (const required of REQUIRED_STRINGS) {
		if (!texts.has(required)) throw new Error(`Required UI string not found by inventory scanner: ${required}`);
	}
}

function main() {
	const args = parseArgs(process.argv.slice(2));
	const clientRoot = resolveClientRoot(args.serverRoot, args.clientRoot);
	const entries = TARGET_FILES.flatMap((file, index) => collectFile(clientRoot, file, index));
	entries.sort((a, b) =>
		a.fileIndex - b.fileIndex || a.line - b.line || a.type.localeCompare(b.type) || a.text.localeCompare(b.text)
	);
	assertRequiredStrings(entries);
	const markdown = renderMarkdown(gitHead(clientRoot), entries);
	if (args.check) {
		if (!fs.existsSync(args.output)) throw new Error(`Committed inventory is missing: ${args.output}`);
		const committed = fs.readFileSync(args.output, 'utf8');
		if (committed !== markdown) {
			throw new Error(`Committed inventory is stale. Regenerate ${path.relative(args.serverRoot, args.output)}`);
		}
		console.log(`Verified ${path.relative(args.serverRoot, args.output)} (${entries.length} entries).`);
		return;
	}
	fs.mkdirSync(path.dirname(args.output), {recursive: true});
	fs.writeFileSync(args.output, markdown);
	console.log(`Wrote ${path.relative(args.serverRoot, args.output)} (${entries.length} entries).`);
}

try {
	main();
} catch (error) {
	console.error(error instanceof Error ? error.stack : error);
	process.exit(1);
}
