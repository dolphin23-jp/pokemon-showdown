# Phase 1 T1-08: mechanically generated Japanese display-name maps

T1-08 populates the display-only API introduced in T1-07 with mechanically generated Japanese names for species, moves, abilities, and items.

## Pinned client revision

The server pins the owned client fork at:

```text
523a5fb38255916f6fb7bcd4b5b3ccaa5414f6eb
```

That fork revision remains based on upstream commit:

```text
085dfabd9bc53c730ac459edf5c28088677adfc2
```

## Generated source

The client generator reads immutable CSV data from:

```text
PokeAPI/pokeapi@227b573712414a86ba299d322fa398fbb2893edc
```

It selects PokeAPI language ID `11`, joins Japanese names to the corresponding English identifiers, and normalizes those identifiers into lowercase alphanumeric lookup IDs. It generates four frozen tables under `window.BattleJapaneseDisplayNames`:

- `species`
- `moves`
- `abilities`
- `items`

The generated tables are read only through the four helpers already exposed by `window.PSDisplayNames`:

- `displaySpeciesName(...)`
- `displayMoveName(...)`
- `displayAbilityName(...)`
- `displayItemName(...)`

The generated tables are embedded into `play.pokemonshowdown.com/js/battle-display-names.js` after the TypeScript API is compiled. Build metadata is written to `play.pokemonshowdown.com/js/battle-display-names.meta.json`.

Generation fails if the source cannot be fetched, if normalized identifiers collide with different Japanese names, or if table sizes fall below these guards:

- species: 1000
- moves: 800
- abilities: 250
- items: 1500

Entries not represented by the source, including some form-specific names, continue to return the canonical English Dex name.

## Safety boundary

The generated data is one-way and display-only.

- `mutates_ids: false`
- `protocol_safe: true`
- no changes under `data/` or `sim/`
- no replacement of normalized IDs
- no changes to WebSocket battle protocol messages
- no use in `/choose` or `/team`
- no use in Team Import/Export
- no Japanese strings passed to foul-play
- no Japanese strings passed to Rust `poke-engine`
- no reverse conversion from Japanese display strings into IDs

## Build verification

`scripts/check-built-client.py` now requires:

- the generated block inside `battle-display-names.js`
- `window.PSDisplayNames`
- `window.BattleJapaneseDisplayNames`
- all four display helper names
- the exact PokeAPI source commit
- the generated metadata artifact
- the expected source repository and language ID
- minimum counts for all four generated tables
- `mutates_ids: false`
- `protocol_safe: true`

## Required regression tests

The server repository continues to require:

- `scripts/test-foul-play-local-login.py`
- `scripts/test-foul-play-battle-fallbacks.py`
- `scripts/smoke-bss-battle.py`
- `scripts/smoke-bss-faint-recovery.py`

The client revision passed its Node.js CI and dedicated Japanese display-name workflow before being pinned here.
