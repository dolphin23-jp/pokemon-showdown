# Phase 1 T1-07: display-only Japanese name API skeleton

T1-07 adds the client-side boundary that later tasks will use to render Japanese Pokémon names without changing normalized IDs or protocol payloads.

## Pinned client revision

The server pins the owned client fork at:

```text
1a5d96a4c05f0f4da766de877f3219b68c51f158
```

That fork commit is based on upstream commit:

```text
085dfabd9bc53c730ac459edf5c28088677adfc2
```

The pin verifier confirms the fork relationship, both exact commits and dates, and that the adopted fork commit descends from the recorded upstream base.

## Browser API

The client exposes a frozen `window.PSDisplayNames` object with four helpers:

- `displaySpeciesName(...)`
- `displayMoveName(...)`
- `displayAbilityName(...)`
- `displayItemName(...)`

Each helper resolves the input through the existing client `Dex`, uses the normalized English ID only as a lookup key, and returns the canonical English Dex name when no Japanese entry is present.

The future generated dataset is read from `window.BattleJapaneseDisplayNames`. T1-07 deliberately does not populate that dataset; T1-08 will generate it mechanically.

## Safety boundary

The API is one-way and display-only.

- it does not mutate the caller input
- it does not mutate Dex entries
- it does not replace normalized IDs
- it is not called by WebSocket outbound code
- it is not used for `/choose` or `/team`
- it is not used for Team Import/Export
- it is not passed to foul-play
- it is not passed to Rust `poke-engine`
- it does not reverse Japanese display names into IDs

## Build verification

`check-built-client.py` requires the Docker image to contain:

- `config/japanese-display-name-api.json`
- `play.pokemonshowdown.com/js/battle-display-names.js`
- a `testclient-new.html` script reference to the compiled API
- all four helper names
- canonical-English fallback
- `mutates_ids: false`
- `protocol_safe: true`

The generated-map presence is reported but is expected to be false in T1-07.

## Required regression tests

The server repository continues to require:

- `scripts/test-foul-play-local-login.py`
- `scripts/test-foul-play-battle-fallbacks.py`
- `scripts/smoke-bss-battle.py`
- `scripts/smoke-bss-faint-recovery.py`

T1-07 does not modify `data/`, `sim/`, battle protocol messages, team serialization, foul-play input, or `poke-engine` input.
