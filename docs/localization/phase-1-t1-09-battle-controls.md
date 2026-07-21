# Phase 1 T1-09: Japanese battle choice controls

T1-09 is the first Phase 1 task that applies the generated Japanese display-name maps to interactive battle UI.

## Pinned client revision

The server pins the owned client fork at:

```text
80c72741b52e91d35ee778982a936ea42526c078
```

That client revision remains based on upstream commit:

```text
085dfabd9bc53c730ac459edf5c28088677adfc2
```

The generated maps remain sourced from:

```text
PokeAPI/pokeapi@227b573712414a86ba299d322fa398fbb2893edc
```

using PokeAPI language ID `11`.

## Localized battle controls

The existing `window.PSDisplayNames` API continues to expose:

- `displaySpeciesName(...)`
- `displayMoveName(...)`
- `displayAbilityName(...)`
- `displayItemName(...)`

T1-09 applies the first two functions to the visible direct text node of these controls:

- `button.movebutton`
- `button[data-tooltip^="switchpokemon|"]`
- `button[data-tooltip^="allypokemon|"]`
- `button[data-tooltip^="activepokemon|"]`

Move buttons are rendered with Japanese move names when available. Switch, team-preview, ally, and active-target buttons are rendered with Japanese species names when their visible label is a canonical species name.

Nicknames, empty slots, forms absent from the generated source, and other unknown labels remain unchanged or use the canonical English Dex name.

A narrowly scoped `MutationObserver` covers controls inserted after page load and text replaced during Preact re-renders.

## Display-only safety boundary

Only the visible direct text node is replaced.

- `data-cmd` is not changed
- `data-tooltip` is not changed
- request JSON is not changed
- move and switch indexes are not changed
- normalized IDs are not changed
- WebSocket battle protocol messages are not changed
- `/choose` is not changed
- `/team` is not changed
- Team Import/Export is not changed
- no Japanese strings are passed to foul-play
- no Japanese strings are passed to Rust `poke-engine`
- no changes are made under `data/` or `sim/`

The generated tables remain under `window.BattleJapaneseDisplayNames`. Display strings are never converted back into protocol IDs.

The machine-readable contract records:

- `display_text_only: true`
- `mutates_commands: false`
- `mutates_tooltips: false`
- `preserves_unknown_names: true`
- `mutates_ids: false`
- `protocol_safe: true`

## Client validation

The pinned client revision passed:

- Node.js CI
- TypeScript strict checking
- ESLint
- generated-map source and count verification
- display-name API tests
- battle-control DOM tests

The battle-control tests prove that:

- `Thunderbolt` is displayed as `10まんボルト`
- `Pikachu` is displayed as `ピカチュウ`
- the nickname `Sparky` is preserved
- `/move 1` and `/switch 1` remain unchanged
- canonical English tooltip payloads remain unchanged
- the observer covers `childList`, `subtree`, and `characterData`

## Server validation

The server repository continues to require:

- `scripts/test-foul-play-local-login.py`
- `scripts/test-foul-play-battle-fallbacks.py`
- `scripts/smoke-bss-battle.py`
- `scripts/smoke-bss-faint-recovery.py`

`scripts/check-built-client.py` verifies the T1-09 contract, source selectors, observer markers, generated maps, fixed source revision, minimum table counts, and the absence of command/tooltip mutation code.

The Render smoke workflow must complete the Docker build, embedded-client verification, Bot login, normal BSS battle, faint recovery, access-gate checks, pinned-client delivery, and iPad-sized browser capture before merge.
