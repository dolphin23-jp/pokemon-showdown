#!/usr/bin/env node
import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import ts from 'typescript';

const args = {
	serverRoot: process.cwd(),
	clientRoot: '',
	serverBaseline: 'a7fa86ebfbdf6e0c7678b01ff826cc1d5e5577ae',
	clientBaseline: 'd2939675265dabb8e42c5b8ade059115ee3086db',
	output: '/tmp/phase3-integration/phase3-boundary-report.json',
};
for (let index = 2; index < process.argv.length; index++) {
	const argument = process.argv[index];
	if (argument === '--server-root') args.serverRoot = process.argv[++index];
	else if (argument === '--client-root') args.clientRoot = process.argv[++index];
	else if (argument === '--server-baseline') args.serverBaseline = process.argv[++index];
	else if (argument === '--client-baseline') args.clientBaseline = process.argv[++index];
	else if (argument === '--output') args.output = process.argv[++index];
	else throw new Error(`Unknown argument: ${argument}`);
}
args.serverRoot = path.resolve(args.serverRoot);
args.clientRoot = path.resolve(args.clientRoot);
args.output = path.resolve(args.output);

const TARGET_FILES = [
	'play.pokemonshowdown.com/src/panel-battle.tsx',
	'play.pokemonshowdown.com/src/panel-popups.tsx',
	'play.pokemonshowdown.com/src/battle-team-editor.tsx',
	'play.pokemonshowdown.com/src/panel-teambuilder.tsx',
	'play.pokemonshowdown.com/src/panel-teambuilder-team.tsx',
	'play.pokemonshowdown.com/src/panel-teamdropdown.tsx',
];

function git(root, command) {
	return execFileSync('git', ['-C', root, ...command], {encoding: 'utf8'}).trim();
}
function changedFiles(root, baseline) {
	const output = git(root, ['diff', '--name-only', `${baseline}..HEAD`]);
	return output ? output.split('\n').filter(Boolean) : [];
}
function fileAt(root, ref, filename) {
	return execFileSync('git', ['-C', root, 'show', `${ref}:${filename}`], {encoding: 'utf8'});
}
function currentFile(root, filename) {
	return fs.readFileSync(path.join(root, filename), 'utf8');
}
function attributeInventory(filename, source) {
	const sourceFile = ts.createSourceFile(filename, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
	const result = [];
	function visit(node) {
		if (ts.isJsxAttribute(node)) {
			const name = node.name.getText(sourceFile);
			if (name === 'data-cmd' || name === 'data-tooltip') {
				result.push({name, initializer: node.initializer?.getText(sourceFile) || ''});
			}
		}
		ts.forEachChild(node, visit);
	}
	visit(sourceFile);
	return result;
}

const serverChanges = changedFiles(args.serverRoot, args.serverBaseline);
const clientChanges = changedFiles(args.clientRoot, args.clientBaseline);
const forbiddenServer = serverChanges.filter(file => file === 'data' || file.startsWith('data/') || file === 'sim' || file.startsWith('sim/'));
const forbiddenClient = clientChanges.filter(file => (
	file === 'data' || file.startsWith('data/') || file.startsWith('play.pokemonshowdown.com/data/') ||
	file === 'sim' || file.startsWith('sim/')
));
if (forbiddenServer.length || forbiddenClient.length) {
	throw new Error(`Protected data/sim paths changed: ${JSON.stringify({forbiddenServer, forbiddenClient})}`);
}

const attributes = {};
for (const filename of TARGET_FILES) {
	const before = attributeInventory(filename, fileAt(args.clientRoot, args.clientBaseline, filename));
	const after = attributeInventory(filename, currentFile(args.clientRoot, filename));
	if (JSON.stringify(before) !== JSON.stringify(after)) {
		throw new Error(`data-cmd/data-tooltip inventory changed in ${filename}`);
	}
	attributes[filename] = {count: after.length, unchanged: true};
}

const teambuilderSources = [
	'battle-team-editor.tsx',
	'panel-teambuilder.tsx',
].map(filename => currentFile(args.clientRoot, `play.pokemonshowdown.com/src/${filename}`)).join('\n');
const importExportMarkers = [
	'Import/Export',
	'Paste exported teams, pokepaste URLs, or JSON here',
	'Save (not allowed for partial exports)',
	'Save changes',
	'Backup',
	"' search results'",
	"' folder'",
];
const missingImportExportMarkers = importExportMarkers.filter(marker => !teambuilderSources.includes(marker));
if (missingImportExportMarkers.length) {
	throw new Error(`Team Import/Export English markers missing: ${JSON.stringify(missingImportExportMarkers)}`);
}

const report = {
	phase: 'Phase 3',
	task: 'T3-08',
	verified: true,
	server: {
		baseline: args.serverBaseline,
		head: git(args.serverRoot, ['rev-parse', 'HEAD']),
		changedFiles: serverChanges,
		protectedDataAndSimChanges: forbiddenServer,
	},
	client: {
		baseline: args.clientBaseline,
		head: git(args.clientRoot, ['rev-parse', 'HEAD']),
		changedFiles: clientChanges,
		protectedDataAndSimChanges: forbiddenClient,
		attributes,
	},
	boundaries: {
		dataAndSimUnchanged: true,
		normalizedIdsProtectedByDataAndSimBoundary: true,
		dataCmdAndTooltipUnchanged: true,
		teamImportExportEnglishMarkersPresent: true,
	},
};
fs.mkdirSync(path.dirname(args.output), {recursive: true});
fs.writeFileSync(args.output, JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report, null, 2));
