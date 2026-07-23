# Phase 3 T3-03: BattleText coverage invariants and smoke tests

## Status

T3-03 is complete in the pinned client revision `3acaa637ca73f64cbf547b5c79e730dbbb857386`.

This task adds regression tests and CI checks only. It does not change any Japanese BattleText template introduced in T3-01 or T3-02.

## Representative BattleText invariant tests

The client test `test/battle-text-japanese.js` now parses representative raw English battle-protocol lines and passes their resulting `args` and `kwArgs` through `BattleTextParser.parseArgsInner` after the Japanese BattleText layer is installed.

The permanent cases cover:

| Namespace | Template | Representative protocol command |
| --- | --- | --- |
| `leftovers` | `heal` | `|-heal|...|[from] item: Leftovers` |
| `disguise` | `block` | `|-block|...|ability: Disguise` |
| `disguise` | `transform` | `|detailschange|...|Mimikyu-Busted, L50|[from] ability: Disguise` |
| `attract` | `start` | `|-start|...|move: Attract` |
| `attract` | `cant` | `|cant|...|Attract` |
| `bide` | `start` | `|-start|...|move: Bide` |
| `bide` | `end` | `|-end|...|move: Bide` |

For every case, the test verifies that:

- the rendered message uses the existing Japanese template
- the raw protocol-derived `args` array is unchanged
- the raw protocol-derived `kwArgs` object is unchanged
- both inputs can be frozen before the parser call without causing a mutation error
- a nickname that is not a species name remains verbatim and is not translated

This protects the display-only localization boundary at the `BattleTextParser` call site. The tests do not rewrite or normalize the protocol values before rendering.

## Coverage regression checker

`scripts/check-phase3-battle-text-coverage.mjs` runs the authoritative T3-00 inventory generator into an isolated temporary file, reads the fresh result, and fails unless both conditions hold:

```text
totalMissing: 0
byNamespace: {}
```

The checker does not rely only on the committed inventory file. If future upstream changes add a runtime key under `data/text/default.ts`, `moves.ts`, `abilities.ts`, or `items.ts` without a matching Japanese template, the newly generated inventory becomes nonzero and CI fails with the missing namespaces and keys.

Run it locally with a checked-out pinned client:

```bash
node scripts/check-phase3-battle-text-coverage.mjs \
  --client-root ../pokemon-showdown-client
```

The success output is a JSON object containing `"totalMissing":0` and an empty `byNamespace` object.

## CI integration

`.github/workflows/phase3-baseline-inventory.yml` now performs all of the following against the pinned client revision:

1. syntax-checks the inventory generators and the coverage checker
2. generates fresh BattleText and UI inventories
3. runs `check-phase3-battle-text-coverage.mjs` and requires zero missing runtime keys
4. verifies that the committed inventories remain current

The existing client Node.js CI runs `test/battle-text-japanese.js`, so the representative protocol-input invariants are also required on every relevant client change.

## Phase 1 boundary regression

T3-03 continues to rely on the Phase 1 invariant suite, including `scripts/test-japanese-protocol-invariants.js`, to verify that localization changes only rendered labels while preserving:

- raw WebSocket battle protocol
- `|request|` JSON
- canonical species, move, ability, and item IDs
- `/choose` and `/team` command payloads
- `data-cmd` and `data-tooltip`
- English Team Import/Export contents
- foul-play inputs
- Rust `poke-engine` state and IDs

No file under `data/` or `sim/` is modified by T3-03.

## Expected result

The authoritative Phase 3 BattleText inventory remains:

```json
{
  "totalMissing": 0,
  "byNamespace": {}
}
```
