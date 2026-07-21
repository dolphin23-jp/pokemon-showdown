# Phase 1 T1-00 baseline

This document records the pre-localization baseline for Phase 1. T1-00 does not change runtime behavior, battle data, simulator IDs, or the battle protocol.

## Baseline commit

The task started from server commit:

- `b506e5db3caff679bde47fece23f3e0aa109a0f0`

The CI artifact generated for the T1-00 pull request records the exact tested head commit as well.

## Current client delivery path

Before Phase 1 client work:

1. `scripts/launcher-server.js` serves the Japanese access and launcher pages.
2. Opening Showdown navigates to `/client.html`.
3. The launcher fetches `https://play.pokemonshowdown.com/testclient-new.html` at runtime.
4. It injects `Config.defaultserver` so the browser connects through `/showdown`.
5. Other client assets are proxied from `play.pokemonshowdown.com`.
6. `/showdown` HTTP and WebSocket traffic is forwarded to the local Showdown server.

This behavior is the visual and functional reference for T1-03 through T1-05.

## Protected interfaces

Phase 1 must preserve all of the following:

- normalized IDs under `data/` and `sim/`
- Showdown battle protocol messages
- browser commands such as `/choose` and `/team`
- team Import/Export text
- the raw protocol consumed by foul-play
- the normalized English IDs serialized into the Rust `poke-engine`

Japanese names may only be returned by display-only functions introduced later in Phase 1. They must not replace internal IDs.

## Required regression tests

Every Phase 1 task must continue to pass:

- `scripts/smoke-bss-battle.py`
- `scripts/smoke-bss-faint-recovery.py`
- `scripts/test-foul-play-local-login.py`
- `scripts/test-foul-play-battle-fallbacks.py`

The Docker build runs the two foul-play unit-style tests. The Render smoke workflow runs both end-to-end battle tests against the built container.

## CI baseline artifacts

The T1-00 workflow records and uploads:

- a machine-readable baseline report
- the authenticated launcher HTML
- the patched client HTML
- an iPad-sized launcher screenshot
- an iPad-sized initial client screenshot
- Docker and container diagnostics already produced by the existing smoke workflow

The screenshots are CI artifacts rather than committed binaries. They provide the comparison reference for T1-05, where the client delivery source changes but the initial browser appearance must remain materially unchanged.

## Known pre-Phase 1 behavior

- The browser login patch sends `/trn <name>,0,`.
- It does not yet send `/language japanese` or a language-bearing `/updatesettings` command.
- Server-side Japanese translation files exist under `translations/japanese/` but are not automatically enabled by the launcher.
- The browser client is not pinned and is obtained from the official host at request time.
- foul-play is pinned to `25c976f05cbf2880eaa579afd6db1dcb2c3b57c6` during the Docker build.

These are baseline observations, not behavior introduced by T1-00.
