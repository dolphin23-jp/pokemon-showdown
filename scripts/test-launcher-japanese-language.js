'use strict';

const assert = require('assert/strict');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const launcherPath = path.resolve(__dirname, 'launcher-server.js');
const launcherSource = fs.readFileSync(launcherPath, 'utf8');
const injectionStart = launcherSource.indexOf('function clientConfigInjection()');
const iifeStart = launcherSource.indexOf('(() => {', injectionStart);
const iifeEnd = launcherSource.indexOf('})();', iifeStart);

assert.notEqual(injectionStart, -1, 'clientConfigInjection must exist');
assert.notEqual(iifeStart, -1, 'client login IIFE must exist');
assert.notEqual(iifeEnd, -1, 'client login IIFE must be complete');

const injectedLoginScript = launcherSource
	.slice(iifeStart, iifeEnd + '})();'.length)
	.replace('${JSON.stringify(DEFAULT_PLAYER_NAME)}', JSON.stringify('FallbackUser'));

function runScenario({ named, challstr, savedName }) {
	const sent = [];
	const stored = new Map();
	if (savedName) stored.set('showdown-player-name', savedName);

	let tick = null;
	let clearCalls = 0;
	const updates = [];
	const loginUpdates = [];
	const user = {
		named,
		challstr,
		update(value) {
			updates.push(value);
		},
		updateLogin(value) {
			loginUpdates.push(value);
		},
	};
	const ps = {
		user,
		send(message) {
			sent.push(message);
		},
	};

	const context = vm.createContext({
		PS: ps,
		localStorage: {
			getItem(key) {
				return stored.get(key) || null;
			},
			setItem(key, value) {
				stored.set(key, value);
			},
		},
		setInterval(callback, delay) {
			assert.equal(delay, 50);
			tick = callback;
			return 17;
		},
		clearInterval(timer) {
			assert.equal(timer, 17);
			clearCalls++;
		},
	});

	vm.runInContext(injectedLoginScript, context);
	assert.ok(tick, 'login patch must install its polling callback');

	return {
		clearCalls: () => clearCalls,
		loginUpdates,
		ps,
		sent,
		stored,
		tick,
		updates,
		user,
	};
}

{
	const scenario = runScenario({ named: false, challstr: 'challenge', savedName: 'BrowserUser' });
	scenario.tick();
	assert.deepEqual(scenario.sent, ['/trn BrowserUser,0,']);
	assert.equal(scenario.user.__personalServerJapaneseLanguageSent, undefined);

	scenario.user.named = true;
	scenario.tick();
	assert.deepEqual(scenario.sent, [
		'/trn BrowserUser,0,',
		'/updatesettings {"language":"japanese"}',
	]);
	assert.equal(scenario.user.__personalServerJapaneseLanguageSent, true);
	assert.equal(scenario.clearCalls(), 1);

	scenario.tick();
	assert.equal(
		scenario.sent.filter(message => message === '/updatesettings {"language":"japanese"}').length,
		1,
		'Japanese settings must not be sent twice for one user model'
	);
}

{
	const scenario = runScenario({ named: true, challstr: '', savedName: 'AlreadyNamed' });
	scenario.tick();
	assert.deepEqual(scenario.sent, ['/updatesettings {"language":"japanese"}']);
	assert.equal(scenario.clearCalls(), 1);
	assert.equal(
		scenario.sent.some(message => message.startsWith('/trn ')),
		false,
		'An already named user must not be renamed'
	);
}

console.log('Launcher Japanese language test passed.');
