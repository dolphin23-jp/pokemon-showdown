#!/usr/bin/env node
import fs from 'node:fs';
const filename = process.argv[2] || 'docs/localization/phase-3-integration-regression.json';
const report = JSON.parse(fs.readFileSync(filename, 'utf8'));
if (report.phase !== 'Phase 3') throw new Error('Unexpected phase');
if (report.task !== 'T3-08') throw new Error('Unexpected task');
if (report.phase3_complete !== true) throw new Error('Phase 3 is not complete');
if (!report.completion_criteria || !Object.values(report.completion_criteria).every(Boolean)) {
	throw new Error('One or more completion criteria are false');
}
if (report.coverage?.totalMissing !== 0 || Object.keys(report.coverage?.byNamespace || {}).length !== 0) {
	throw new Error('Final BattleText coverage is incomplete');
}
if (report.browser?.teambuilder?.importExport?.containsJapanese !== false) {
	throw new Error('Team Import/Export did not remain canonical English');
}
if (!Array.isArray(report.screenshots) || report.screenshots.length < 7) throw new Error('Screenshot evidence is incomplete');
for (const screenshot of report.screenshots) {
	if (screenshot.width !== 1280 || screenshot.height !== 900 || !/^[0-9a-f]{64}$/.test(screenshot.sha256)) {
		throw new Error(`Invalid screenshot metadata: ${JSON.stringify(screenshot)}`);
	}
}
console.log(`Verified ${filename}: Phase 3 complete`);
