# Phase 3 T3-00 baseline inventory

## Status

Phase 3 T3-00 records the remaining English battle narration and UI chrome in the pinned Japanese client. It is an inventory-only task: no runtime localization, simulator data, protocol, command, team, or identifier behavior is changed.

The recorded baseline is:

- server input SHA: `39cc33901269494f65c9da90bedf90fdf2c9d804`
- pinned client SHA: `d2939675265dabb8e42c5b8ade059115ee3086db`
- missing battle-text templates: 452 keys across 312 namespaces
- hard-coded UI chrome entries: 319

The machine-readable and reviewable outputs are:

- `docs/localization/phase-3-battle-text-inventory.json`
- `docs/localization/phase-3-ui-chrome-inventory.md`

These files are the Phase 3 source of truth for T3-01 and later translation and regression tasks.

## Battle-text inventory

`scripts/generate-phase3-battle-text-inventory.mjs` reads:

- `data/text/default.ts`
- `data/text/moves.ts`
- `data/text/abilities.ts`
- `data/text/items.ts`
- the pinned client's `play.pokemonshowdown.com/src/battle-text-ja.js`

The generator reconstructs the English `BattleText` namespace/key shape using the same `assignData` behavior as the client's `build-tools/build-indexes` script. In particular, it intentionally reproduces the original `genN` branch condition that checks `key` rather than `modKey`; therefore `descGenN` and `shortDescGenN` keys are first generated exactly as the client build would generate them.

After reconstruction, keys matching `^(desc|shortDesc)(Gen\d)?$` are removed from the missing-key inventory because those descriptive fields are not battle-log templates. All remaining namespace/key pairs are compared with `JAPANESE_BATTLE_TEXT`.

The committed result contains the expected sentinel gaps:

- `leftovers.heal`
- `disguise.block`
- `disguise.transform`
- all six current `attract` gaps: `activate`, `cant`, `end`, `endFromItem`, `start`, and `startFromItem`

The JSON records both repository SHAs and sorts namespaces and keys deterministically.

## UI chrome inventory

`scripts/generate-phase3-ui-chrome-inventory.mjs` uses the TypeScript AST to inspect:

- `play.pokemonshowdown.com/src/panel-battle.tsx`
- `play.pokemonshowdown.com/src/panel-popups.tsx`
- `play.pokemonshowdown.com/src/battle-team-editor.tsx`
- `play.pokemonshowdown.com/src/panel-teambuilder.tsx`
- `play.pokemonshowdown.com/src/panel-teambuilder-team.tsx`
- `play.pokemonshowdown.com/src/panel-teamdropdown.tsx`

For `panel-popups.tsx`, the scan is intentionally limited to `BattleForfeitPanel` and the adjacent `ReplacePlayerPanel`; unrelated login, settings, moderation, and profile popups are not part of this Phase 3 battle/Teambuilder baseline.

The scanner records:

- directly rendered JSX text
- static renderable JSX expression branches
- `placeholder` attributes
- general `title` attributes, excluding elements carrying `data-tooltip`
- static `room.notify(...)` title/body strings

It excludes `data-cmd`, `data-tooltip`, species/move/ability/item display names, and Team Import/Export contents. The generated list records `file:line | type | current English string` and contains the required sentinels: `Battle`, `Switch`, `Team`, `Cancel`, `Skip animation`, `Main menu`, `Rematch`, `Move to center`, and `Forfeiting makes you lose the battle. Are you sure?`.

The 319 UI entries are distributed as follows:

| Client source | Entries |
| --- | ---: |
| `panel-battle.tsx` | 101 |
| `panel-popups.tsx` | 8 |
| `battle-team-editor.tsx` | 106 |
| `panel-teambuilder.tsx` | 38 |
| `panel-teambuilder-team.tsx` | 43 |
| `panel-teamdropdown.tsx` | 23 |

## Regeneration

With the server repository as the current directory and the pinned client checked out next to it:

```bash
node scripts/generate-phase3-battle-text-inventory.mjs \
  --client-root ../pokemon-showdown-client
node scripts/generate-phase3-ui-chrome-inventory.mjs \
  --client-root ../pokemon-showdown-client
```

To verify committed outputs without rewriting them:

```bash
node scripts/generate-phase3-battle-text-inventory.mjs \
  --client-root ../pokemon-showdown-client \
  --check
node scripts/generate-phase3-ui-chrome-inventory.mjs \
  --client-root ../pokemon-showdown-client \
  --check
```

The dedicated `Phase 3 baseline inventory` workflow checks out the client revision pinned by `config/pokemon-showdown-client.json`, regenerates both inventories, verifies the committed files, and uploads the generated copies as a CI artifact.

## Protected boundaries

T3-00 does not modify:

- `data/` or `sim/`
- `battle-text-ja.js` or any client panel implementation
- species, move, ability, or item IDs
- WebSocket battle protocol data
- `/choose` or `/team`
- `data-cmd` or `data-tooltip`
- Team Import/Export data
- foul-play input or Rust `poke-engine` state
