# Phase 1 T1-02: fork and pin pokemon-showdown-client

T1-02 establishes a separately owned client source and records one immutable revision for all later localization work.

## Repositories and revision

- Fork: `dolphin23-jp/pokemon-showdown-client`
- Upstream: `smogon/pokemon-showdown-client`
- Pinned commit: `085dfabd9bc53c730ac459edf5c28088677adfc2`
- Upstream commit date: `2026-07-17T04:21:54Z`

The machine-readable source of truth is `config/pokemon-showdown-client.json`.

## CI verification

`scripts/check-pinned-client.py --verify-remote` requires all of the following:

1. the configured fork repository exists
2. GitHub reports it as a fork
3. its parent is exactly `smogon/pokemon-showdown-client`
4. the complete pinned SHA resolves in the fork
5. the same SHA resolves in the upstream repository

The Render smoke workflow performs this check before building the existing application image.

## Scope boundary

T1-02 does not build or serve the forked client. Those changes remain separate tasks:

- T1-03 builds the fixed client in Docker
- T1-04 adds local static delivery
- T1-05 replaces runtime retrieval and proxying with the fixed local client

Until those tasks are completed, `/client.html` still retrieves `testclient-new.html` and proxies static assets from `play.pokemonshowdown.com`.

T1-02 does not change `data/`, `sim/`, normalized IDs, battle protocol messages, `/choose`, `/team`, team Import/Export, foul-play inputs, or Rust `poke-engine` inputs.

## Updating the pin

A future pin update must be reviewed as its own task. Change the full 40-character SHA and the recorded upstream commit date together, then run the remote verification and the existing regression suite. Do not use a moving branch or tag as the build input.
