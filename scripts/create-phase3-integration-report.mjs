#!/usr/bin/env node
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

const args = {
	artifactRoot: '/tmp/phase3-integration',
	output: 'docs/localization/phase-3-integration-regression.json',
	serverSha: process.env.PHASE3_TARGET_SHA || '',
	clientSha: '',
	runId: process.env.GITHUB_RUN_ID || '',
};
for (let index = 2; index < process.argv.length; index++) {
	const argument = process.argv[index];
	if (argument === '--artifact-root') args.artifactRoot = process.argv[++index];
	else if (argument === '--output') args.output = process.argv[++index];
	else if (argument === '--server-sha') args.serverSha = process.argv[++index];
	else if (argument === '--client-sha') args.clientSha = process.argv[++index];
	else if (argument === '--run-id') args.runId = process.argv[++index];
	else throw new Error(`Unknown argument: ${argument}`);
}
args.artifactRoot = path.resolve(args.artifactRoot);
args.output = path.resolve(args.output);

function readJSON(filename) {
	return JSON.parse(fs.readFileSync(path.join(args.artifactRoot, filename), 'utf8'));
}
function readStatus(filename) {
	const value = fs.readFileSync(path.join(args.artifactRoot, filename), 'utf8').trim();
	return {value: Number(value), passed: value === '0'};
}
function imageInfo(filename) {
	const filePath = path.join(args.artifactRoot, filename);
	const data = fs.readFileSync(filePath);
	if (!data.subarray(0, 8).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]))) {
		throw new Error(`Invalid PNG signature: ${filename}`);
	}
	return {
		filename,
		bytes: data.length,
		width: data.readUInt32BE(16),
		height: data.readUInt32BE(20),
		sha256: crypto.createHash('sha256').update(data).digest('hex'),
	};
}

const statuses = {
	dockerCleanBuild: readStatus('docker-clean-build.status'),
	clientTests: readStatus('client-tests.status'),
	coverage: readStatus('phase3-coverage.status'),
	protocol: readStatus('protocol-invariants.status'),
	boundaries: readStatus('boundary-audit.status'),
	battleBrowser: readStatus('battle-browser.status'),
	teambuilderBrowser: readStatus('teambuilder-browser.status'),
};
const battle = readJSON('phase3-browser-integration.json');
const teambuilder = readJSON('japanese-teambuilder-report.json');
const boundaries = readJSON('phase3-boundary-report.json');
const workflows = readJSON('phase3-workflow-runs.json');
const coverage = readJSON('phase-3-battle-text-inventory.json');

const screenshotFiles = [
	'phase3-battle-start.png',
	'phase3-battle-switch.png',
	'phase3-battle-leftovers.png',
	'phase3-forfeit-dialog.png',
	'phase3-battle-result.png',
	'japanese-teambuilder-form.png',
	'japanese-teambuilder-import-export.png',
];
const screenshots = screenshotFiles.map(imageInfo);
for (const screenshot of screenshots) {
	if (screenshot.width !== 1280 || screenshot.height !== 900) {
		throw new Error(`Unexpected screenshot dimensions: ${JSON.stringify(screenshot)}`);
	}
}

const completionCriteria = {
	docker_clean_build: statuses.dockerCleanBuild.passed,
	phase3_battle_text_total_missing_zero: statuses.coverage.passed && coverage.totalMissing === 0,
	client_full_regression_suite: statuses.clientTests.passed,
	canonical_protocol_and_commands: statuses.protocol.passed,
	protected_boundaries_unchanged: statuses.boundaries.passed && boundaries.verified === true,
	battle_start_switch_move_item_forfeit_result_verified: statuses.battleBrowser.passed && battle.verified === true,
	teambuilder_labels_verified: statuses.teambuilderBrowser.passed && teambuilder.verified === true,
	team_import_export_remains_english: teambuilder.importExport?.containsJapanese === false,
	phase1_and_required_ci_green: workflows.all_required_workflows_successful === true,
	all_screenshots_valid: screenshots.length === screenshotFiles.length,
};
const phase3Complete = Object.values(completionCriteria).every(Boolean);
if (!phase3Complete) {
	throw new Error(`Phase 3 completion criteria failed: ${JSON.stringify(completionCriteria)}`);
}

const report = {
	phase: 'Phase 3',
	task: 'T3-08',
	phase3_complete: true,
	validated_server_head: args.serverSha || workflows.target_sha,
	pinned_client_sha: args.clientSha || boundaries.client.head,
	integration_workflow_run_id: args.runId ? Number(args.runId) : null,
	completion_criteria: completionCriteria,
	status_files: statuses,
	coverage: {
		totalMissing: coverage.totalMissing,
		byNamespace: coverage.byNamespace,
		generatedFromServerSha: coverage.generatedFromServerSha,
		generatedFromClientSha: coverage.generatedFromClientSha,
	},
	browser: {
		battle,
		teambuilder,
	},
	boundaries,
	workflow_runs: workflows.required_workflows,
	screenshots,
};
fs.mkdirSync(path.dirname(args.output), {recursive: true});
fs.writeFileSync(args.output, JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report, null, 2));
