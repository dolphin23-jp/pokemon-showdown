#!/usr/bin/env node

import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import ts from 'typescript';

const SCRIPT_PATH = fileURLToPath(import.meta.url);
const DEFAULT_SERVER_ROOT = path.resolve(path.dirname(SCRIPT_PATH), '..');
const TARGETS = [
	{
		file: 'play.pokemonshowdown.com/src/panel-battle.tsx',
		appliedGroups: ['BattleChromeSources', 'SharedChromeSources'],
	},
	{
		file: 'play.pokemonshowdown.com/src/panel-popups.tsx',
		classes: ['BattleForfeitPanel', 'ReplacePlayerPanel'],
	},
	{file: 'play.pokemonshowdown.com/src/battle-team-editor.tsx'},
	{file: 'play.pokemonshowdown.com/src/panel-teambuilder.tsx'},
	{file: 'play.pokemonshowdown.com/src/panel-teambuilder-team.tsx'},
	{file: 'play.pokemonshowdown.com/src/panel-teamdropdown.tsx'},
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
		if (TARGETS.every(target => fs.existsSync(path.join(candidate, target.file)))) return candidate;
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

function renderedExpressionStrings(expression) {
	const results = [];
	function collect(node) {
		const text = staticText(node);
		if (text !== null) {
			results.push([node, text]);
			return;
		}
		if (ts.isParenthesizedExpression(node) || ts.isAsExpression(node) ||
			ts.isTypeAssertionExpression(node) || ts.isNonNullExpression(node)) {
			collect(node.expression);
			return;
		}
		if (ts.isConditionalExpression(node)) {
			collect(node.whenTrue);
			collect(node.whenFalse);
			return;
		}
		if (ts.isArrayLiteralExpression(node)) {
			for (const element of node.elements) collect(element);
			return;
		}
		if (ts.isBinaryExpression(node) && (
			node.operatorToken.kind === ts.SyntaxKind.AmpersandAmpersandToken ||
			node.operatorToken.kind === ts.SyntaxKind.BarBarToken ||
			node.operatorToken.kind === ts.SyntaxKind.QuestionQuestionToken
		)) {
			collect(node.right);
		}
	}
	collect(expression);
	return results;
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

function collectNotify(call, sourceFile, addEntry) {
	if (!ts.isPropertyAccessExpression(call.expression) || call.expression.name.text !== 'notify') return;
	const receiver = call.expression.expression.getText(sourceFile);
	if (!/(?:^|\.)room$|\.room\b/.test(receiver)) return;
	const [first, second] = call.arguments;
	if (first && ts.isObjectLiteralExpression(first)) {
		for (const property of first.properties) {
			if (!ts.isPropertyAssignment(property)) continue;
			const key = property.name.getText(sourceFile).replace(/^[ '"]|['"]$/g, '');
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

function targetRoots(sourceFile, target) {
	if (!target.classes) return [sourceFile];
	const roots = [];
	const found = new Set();
	for (const statement of sourceFile.statements) {
		if (!ts.isClassDeclaration(statement) || !statement.name) continue;
		if (!target.classes.includes(statement.name.text)) continue;
		roots.push(statement);
		found.add(statement.name.text);
	}
	const missing = target.classes.filter(className => !found.has(className));
	if (missing.length) {
		throw new Error(`Missing scoped class in ${target.file}: ${missing.join(', ')}`);
	}
	return roots;
}

function readFrameworkSources(clientRoot) {
	const filePath = path.join(clientRoot, 'play.pokemonshowdown.com/src/client-ui-ja-strings.ts');
	const source = fs.readFileSync(filePath, 'utf8');
	const sourceFile = ts.createSourceFile(filePath, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
	const groups = new Map();
	for (const statement of sourceFile.statements) {
		if (!ts.isVariableStatement(statement)) continue;
		for (const declaration of statement.declarationList.declarations) {
			if (!ts.isIdentifier(declaration.name) || !declaration.name.text.endsWith('Sources')) continue;
			let initializer = declaration.initializer;
			if (initializer && ts.isAsExpression(initializer)) initializer = initializer.expression;
			if (!initializer || !ts.isObjectLiteralExpression(initializer)) {
				throw new Error(`${declaration.name.text} must be an object literal`);
			}
			const entries = new Map();
			for (const property of initializer.properties) {
				if (!ts.isPropertyAssignment(property) || !ts.isArrayLiteralExpression(property.initializer)) continue;
				const [englishNode] = property.initializer.elements;
				if (!englishNode || !ts.isStringLiteral(englishNode)) continue;
				entries.set(property.name.getText(sourceFile), englishNode.text);
			}
			groups.set(declaration.name.text, entries);
		}
	}
	return groups;
}

function collectFile(clientRoot, target, fileIndex, groups) {
	const filePath = path.join(clientRoot, target.file);
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
		entries.push({file: target.file, fileIndex, line, type, text});
	}
	function addAppliedReference(node) {
		if (!target.appliedGroups || !ts.isPropertyAccessExpression(node) || !ts.isIdentifier(node.expression)) return;
		const groupName = node.expression.text.replace(/JA$/, 'Sources');
		if (!target.appliedGroups.includes(groupName)) return;
		const group = groups.get(groupName);
		if (!group) throw new Error(`Missing ${groupName} for ${target.file}`);
		const english = group.get(node.name.text);
		if (!english) throw new Error(`Unknown ${node.expression.text}.${node.name.text} in ${target.file}`);
		let type = 'label';
		if (ts.isJsxExpression(node.parent) && ts.isJsxAttribute(node.parent.parent)) {
			type = jsxAttributeName(node.parent.parent);
		} else {
			let current = node.parent;
			while (current && current !== sourceFile) {
				if (ts.isPropertyAssignment(current)) {
					const key = current.name.getText(sourceFile).replace(/^['\"]|['\"]$/g, '');
					if (key === 'title' || key === 'body') {
						type = 'notify';
						break;
					}
				}
				current = current.parent;
			}
		}
		addEntry(node, type, english);
	}
	function visit(node) {
		if (ts.isJsxText(node)) {
			addEntry(node, 'label', node.getText(sourceFile));
		} else if (ts.isJsxExpression(node) && node.expression &&
			(ts.isJsxElement(node.parent) || ts.isJsxFragment(node.parent))) {
			for (const [literalNode, text] of renderedExpressionStrings(node.expression)) {
				addEntry(literalNode, 'label', text);
			}
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
		addAppliedReference(node);
		ts.forEachChild(node, visit);
	}
	for (const root of targetRoots(sourceFile, target)) visit(root);
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
		'This inventory contains hard-coded English UI chrome from the Phase 3 battle and Teambuilder scope. It includes JSX labels, placeholders, general title attributes, and `room.notify(...)` title/body text. For `panel-popups.tsx`, the scan is intentionally limited to `BattleForfeitPanel` and the adjacent `ReplacePlayerPanel`. It excludes `data-cmd`, `data-tooltip`, translated species/move/ability/item names, and Team Import/Export contents.',
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
	const groups = readFrameworkSources(clientRoot);
	const entries = TARGETS.flatMap((target, index) => collectFile(clientRoot, target, index, groups));
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
