/* eslint-disable no-template-curly-in-string */

'use strict';

const fs = require('fs');
const path = require('path');
const ts = require('typescript');

const ROOT = path.resolve(__dirname, '..');
const JAPANESE_DIR = path.join(ROOT, 'translations', 'japanese');
const SERVER_DIR = path.join(ROOT, 'server');
const OUTPUT_METHODS = new Set([
	'sendReply', 'sendReplyBox', 'errorReply', 'popupReply', 'popup',
]);

function parseArgs(argv) {
	const args = { checkFixed: false, jsonOutput: '', markdownOutput: '' };
	for (let i = 0; i < argv.length; i++) {
		const arg = argv[i];
		if (arg === '--check-fixed') args.checkFixed = true;
		else if (arg === '--json-output') args.jsonOutput = argv[++i];
		else if (arg === '--markdown-output') args.markdownOutput = argv[++i];
		else throw new Error(`Unknown argument: ${arg}`);
	}
	return args;
}

function walk(dir, predicate) {
	const files = [];
	for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
		const full = path.join(dir, entry.name);
		if (entry.isDirectory()) files.push(...walk(full, predicate));
		else if (predicate(full)) files.push(full);
	}
	return files.sort();
}

function sourceFile(file) {
	return ts.createSourceFile(
		file,
		fs.readFileSync(file, 'utf8'),
		ts.ScriptTarget.Latest,
		true,
		ts.ScriptKind.TS
	);
}

function propertyNameText(name) {
	if (ts.isStringLiteral(name) || ts.isNumericLiteral(name) || ts.isIdentifier(name)) {
		return name.text;
	}
	return null;
}

function literalText(node) {
	if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) return node.text;
	return null;
}

function extractDictionary() {
	const entries = new Map();
	const duplicateKeys = [];
	for (const file of walk(JAPANESE_DIR, f => f.endsWith('.ts'))) {
		const sf = sourceFile(file);
		function visit(node) {
			if (ts.isPropertyAssignment(node) && propertyNameText(node.name) === 'strings' && ts.isObjectLiteralExpression(node.initializer)) {
				for (const prop of node.initializer.properties) {
					if (!ts.isPropertyAssignment(prop)) continue;
					const key = propertyNameText(prop.name);
					const value = literalText(prop.initializer);
					if (key === null || value === null) continue;
					const line = sf.getLineAndCharacterOfPosition(prop.getStart(sf)).line + 1;
					const record = {
						key,
						value,
						file: path.relative(ROOT, file).replaceAll(path.sep, '/'),
						line,
					};
					if (entries.has(key)) duplicateKeys.push([entries.get(key), record]);
					entries.set(key, record);
				}
			}
			ts.forEachChild(node, visit);
		}
		visit(sf);
	}
	return { entries, duplicateKeys };
}

function templateKey(template, sf) {
	if (ts.isNoSubstitutionTemplateLiteral(template)) return template.text;
	if (!ts.isTemplateExpression(template)) return null;
	let result = template.head.text;
	for (const span of template.templateSpans) {
		result += '${' + span.expression.getText(sf) + '}' + span.literal.text;
	}
	return result;
}

function enclosingCommand(node) {
	for (let cur = node.parent; cur; cur = cur.parent) {
		if (ts.isMethodDeclaration(cur) && cur.name) return propertyNameText(cur.name) || cur.name.getText();
		if (ts.isPropertyAssignment(cur) && cur.name) return propertyNameText(cur.name) || cur.name.getText();
	}
	return '';
}

function priority(file, command, kind) {
	if (kind === 'empty' || command === 'userlist' || command === 'language') return 'P0';
	if (file.startsWith('server/chat-commands/')) return 'P1';
	if (file.startsWith('server/chat-plugins/')) return 'P2';
	return 'P3';
}

function isEnglishText(text) {
	return /[A-Za-z]{3}/.test(text) && !text.startsWith('|') && !text.startsWith('/');
}

function scanServer(dictionary) {
	const taggedKeys = [];
	const directEnglish = [];
	const files = walk(SERVER_DIR, f => f.endsWith('.ts'));
	for (const file of files) {
		const rel = path.relative(ROOT, file).replaceAll(path.sep, '/');
		if (rel.startsWith('server/translations/')) continue;
		const sf = sourceFile(file);
		function visit(node) {
			if (ts.isTaggedTemplateExpression(node) && ts.isPropertyAccessExpression(node.tag) && node.tag.name.text === 'tr') {
				const key = templateKey(node.template, sf);
				if (key !== null) {
					const line = sf.getLineAndCharacterOfPosition(node.getStart(sf)).line + 1;
					taggedKeys.push({
						key,
						file: rel,
						line,
						command: enclosingCommand(node),
					});
				}
			}
			if (ts.isCallExpression(node) && ts.isPropertyAccessExpression(node.expression)) {
				const method = node.expression.name.text;
				if (OUTPUT_METHODS.has(method) && node.arguments.length) {
					const first = node.arguments[0];
					let text = literalText(first);
					if (text === null && ts.isTemplateExpression(first)) text = templateKey(first, sf);
					if (text !== null && isEnglishText(text)) {
						const line = sf.getLineAndCharacterOfPosition(node.getStart(sf)).line + 1;
						directEnglish.push({
							text,
							method,
							file: rel,
							line,
							command: enclosingCommand(node),
							priority: priority(rel, enclosingCommand(node), 'direct'),
						});
					}
				}
			}
			ts.forEachChild(node, visit);
		}
		visit(sf);
	}

	const seen = new Set();
	const missing = [];
	for (const item of taggedKeys) {
		if (dictionary.has(item.key) || seen.has(item.key)) continue;
		seen.add(item.key);
		missing.push({
			...item,
			priority: priority(item.file, item.command, 'missing'),
		});
	}
	const sortItems = items => items.sort((a, b) =>
		a.priority.localeCompare(b.priority) || a.file.localeCompare(b.file) || a.line - b.line || (a.key || a.text).localeCompare(b.key || b.text)
	);
	return {
		taggedKeys,
		missing: sortItems(missing),
		directEnglish: sortItems(directEnglish),
	};
}

function placeholders(text) {
	return [...text.matchAll(/\$\{([^}]+)\}/g)].map(match => match[1]).sort();
}

function assertFixed(dictionary, serverScan) {
	const errors = [];
	const requireValue = (key, expected) => {
		const entry = dictionary.get(key);
		if (!entry) errors.push(`Missing Japanese dictionary key: ${key}`);
		else if (entry.value !== expected) errors.push(`Unexpected Japanese value for ${key}: ${entry.value}`);
	};

	requireValue('Tiering FAQ', 'ティア制度に関するよくある質問');
	requireValue('Badge FAQ', 'バッジに関するよくある質問');
	requireValue('#${number} in queue', 'キューの${number}番目');
	requireValue(
		'There is <strong style="color:#24678d">${count}</strong> user in this room:<br />',
		'この部屋には<strong style="color:#24678d">${count}</strong>人のユーザーがいます。<br />'
	);
	requireValue(
		'There are <strong style="color:#24678d">${count}</strong> users in this room:<br />',
		'この部屋には<strong style="color:#24678d">${count}</strong>人のユーザーがいます。<br />'
	);

	for (const entry of dictionary.values()) {
		if (/\bPlease\b/.test(entry.value)) errors.push(`English Please remains in ${entry.file}:${entry.line}`);
		if (entry.value.includes('/ignire')) errors.push(`/ignire remains in ${entry.file}:${entry.line}`);
		if (entry.value.includes('Room FAQ')) errors.push(`Room FAQ remains in Japanese value ${entry.file}:${entry.line}`);
		if (placeholders(entry.key).join('\u0000') !== placeholders(entry.value).join('\u0000')) {
			if (entry.key === '#${number} in queue') {
				errors.push(`Placeholder mismatch remains in ${entry.file}:${entry.line}`);
			}
		}
	}

	const core = fs.readFileSync(path.join(ROOT, 'server/chat-commands/core.ts'), 'utf8');
	if (core.includes('There ${Chat.plural(userList, "are", "is")}')) {
		errors.push('/userlist still builds an untranslated English sentence');
	}
	if (!core.includes('this.tr`There is <strong style="color:#24678d">${count}</strong> user in this room:<br />`')) {
		errors.push('/userlist singular translation boundary is missing');
	}
	if (!core.includes('this.tr`There are <strong style="color:#24678d">${count}</strong> users in this room:<br />`')) {
		errors.push('/userlist plural translation boundary is missing');
	}
	if (serverScan.directEnglish.some(item => item.command === 'userlist')) {
		errors.push('/userlist remains in the direct-English inventory');
	}
	if (errors.length) throw new Error(errors.join('\n'));
}

function countByPriority(items) {
	const result = { P0: 0, P1: 0, P2: 0, P3: 0 };
	for (const item of items) result[item.priority]++;
	return result;
}

function markdown(report) {
	const lines = [
		'# Phase 2 Japanese server translation inventory',
		'',
		`Generated from commit: \`${process.env.GITHUB_SHA || 'local'}\``,
		'',
		'## Summary',
		'',
		`- Japanese dictionary keys: ${report.summary.dictionaryKeys}`,
		`- Empty Japanese values: ${report.summary.emptyValues}`,
		`- Tagged translation keys missing from Japanese: ${report.summary.missingKeys}`,
		`- Direct English output candidates bypassing tr: ${report.summary.directEnglishCandidates}`,
		'',
		'Priority means: P0 = login/common command or correctness blocker; P1 = common public command; P2 = room/plugin/staff workflow; P3 = uncommon/internal.',
		'',
	];
	const section = (title, items, field) => {
		lines.push(`## ${title}`, '');
		if (!items.length) {
			lines.push('None.', '');
			return;
		}
		lines.push('| Priority | Source | Command | Text |', '| --- | --- | --- | --- |');
		for (const item of items) {
			const text = String(item[field]).replaceAll('|', '\\|').replaceAll('\n', ' ');
			lines.push(`| ${item.priority} | \`${item.file}:${item.line}\` | \`${item.command || '-'}\` | ${text} |`);
		}
		lines.push('');
	};
	section('Empty dictionary values', report.emptyValues, 'key');
	section('Missing Japanese dictionary keys', report.missingKeys.slice(0, 100), 'key');
	section('Direct English output candidates', report.directEnglishCandidates.slice(0, 100), 'text');
	lines.push('The JSON report contains the complete, untruncated inventories.');
	return lines.join('\n') + '\n';
}

function main() {
	const args = parseArgs(process.argv.slice(2));
	const { entries, duplicateKeys } = extractDictionary();
	const serverScan = scanServer(entries);
	const emptyValues = [...entries.values()]
		.filter(entry => entry.value === '')
		.map(entry => ({ ...entry, priority: priority(entry.file, '', 'empty') }))
		.sort((a, b) => a.file.localeCompare(b.file) || a.line - b.line);
	const report = {
		task: 'Phase 2 server dictionary audit',
		generatedAt: new Date().toISOString(),
		commit: process.env.GITHUB_SHA || 'local',
		summary: {
			dictionaryKeys: entries.size,
			duplicateKeys: duplicateKeys.length,
			emptyValues: emptyValues.length,
			taggedTranslationKeys: serverScan.taggedKeys.length,
			missingKeys: serverScan.missing.length,
			directEnglishCandidates: serverScan.directEnglish.length,
			missingByPriority: countByPriority(serverScan.missing),
			directEnglishByPriority: countByPriority(serverScan.directEnglish),
		},
		fixedScope: {
			tieringFaq: true,
			badgeFaq: true,
			pleaseResidue: true,
			ignoreTypo: true,
			numberInterpolation: true,
			roomFaqResidue: true,
			userlistTranslationBoundary: true,
		},
		emptyValues,
		missingKeys: serverScan.missing,
		directEnglishCandidates: serverScan.directEnglish,
	};

	if (args.checkFixed) assertFixed(entries, serverScan);
	const payload = JSON.stringify(report, null, 2) + '\n';
	if (args.jsonOutput) {
		fs.mkdirSync(path.dirname(path.resolve(args.jsonOutput)), { recursive: true });
		fs.writeFileSync(args.jsonOutput, payload);
	}
	if (args.markdownOutput) {
		fs.mkdirSync(path.dirname(path.resolve(args.markdownOutput)), { recursive: true });
		fs.writeFileSync(args.markdownOutput, markdown(report));
	}
	process.stdout.write(payload);
}

main();
