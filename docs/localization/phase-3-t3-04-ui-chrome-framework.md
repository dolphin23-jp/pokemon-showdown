# Phase 3 T3-04: Japanese UI chrome framework

## Status

T3-04 is implemented in the pinned client revision `05135ec3cf35211799fdc68e1d142ed2a8609086`.

This task creates the shared Japanese-string framework only. It does not yet replace any JSX label in the battle screen, forfeit dialog, or Teambuilder; those integrations remain scoped to T3-05, T3-06, and T3-07.

## Design decision

Phase 1 used a `MutationObserver` for move and Pokémon buttons because those controls contain dynamic names derived from battle state, nicknames, and protocol data. Their canonical values therefore had to remain separate from their localized visible text.

The T3-00 UI chrome inventory contains static labels, placeholders, ordinary title attributes, and static notification text. These values do not carry canonical IDs or user input. T3-04 therefore uses direct TypeScript constants that later tasks can import into JSX and notification calls.

The framework does not inspect or mutate the DOM. It does not rewrite `data-cmd`, `data-tooltip`, WebSocket messages, request JSON, `/choose`, `/team`, Team Import/Export, or any simulator value.

## Client module

The client adds:

```text
play.pokemonshowdown.com/src/client-ui-ja-strings.ts
```

Every inventory phrase is represented by one semantic key paired with:

1. the exact English source string recorded by the T3-00 scanner
2. the Japanese display string used by later integration tasks

The public exports expose Japanese-only, readonly objects suitable for direct JSX substitution:

- `SharedChromeJA`
- `BattleChromeJA`
- `ForfeitDialogJA`
- `TeambuilderChromeJA`
- `TeambuilderListChromeJA`
- `TeambuilderTeamChromeJA`
- `TeamDropdownChromeJA`

`UIChromeJAGroups` provides the same exports as one grouped object. `UIChromeJAByEnglish` provides an English-to-Japanese index for inventory traceability and tooling; application code should normally use the semantic grouped keys.

Example future integration:

```tsx
import { BattleChromeJA, SharedChromeJA } from './client-ui-ja-strings';

<button data-cmd="/cancel">{SharedChromeJA.cancel}</button>
<h3>{BattleChromeJA.battleTab}</h3>
```

Only the rendered child text changes in this example. The command attribute remains `/cancel`.

## Duplicate handling

The T3-00 inventory currently contains 319 occurrences but 227 unique English strings. Repeated strings such as `Close`, `Cancel`, `Loading...`, `Back`, and `Tera` are defined once in `SharedChromeJA` and reused wherever the same English source appears.

The framework rejects duplicate English source definitions when constructing `UIChromeJAByEnglish`. This enforces the T3-04 rule that one English phrase maps to one constant key.

## Inventory coverage test

The client adds:

```text
test/client-ui-ja-strings.js
```

The test independently applies the T3-00 AST scanning rules to the six source files in scope:

- `panel-battle.tsx`
- `panel-popups.tsx`, limited to `BattleForfeitPanel` and `ReplacePlayerPanel`
- `battle-team-editor.tsx`
- `panel-teambuilder.tsx`
- `panel-teambuilder-team.tsx`
- `panel-teamdropdown.tsx`

It verifies all of the following:

- the current scan contains 319 entries
- those entries contain 227 unique English strings
- the framework contains exactly 227 English/Japanese pairs
- the two English-string sets are identical
- no English source is assigned to multiple keys
- every key has a nonempty Japanese value
- no value remains English-only, except the language-neutral keyboard label `Esc`

The test is part of the existing client `npm test` command, alongside the TypeScript build and ESLint checks.

## Dynamic notification text

Static notification titles that appear in the inventory have constants in `BattleChromeJA`. Notification bodies that combine static text with an opponent name should be assembled in natural Japanese order when T3-05 applies the framework, for example by placing the opponent name before the Japanese sentence rather than appending it to an English-order fragment.

T3-04 does not change notification behavior or perform this integration yet.

## Protected boundaries

T3-04 modifies no component logic and no existing JSX source. In particular, it does not change:

- conditions, event handlers, component state, or room state
- `data-cmd`, `data-tooltip`, or other command-bearing attributes
- `data/` or `sim/`
- species, move, ability, item, or format IDs
- raw WebSocket battle protocol or `|request|` JSON
- `/choose` or `/team`
- Team Import/Export contents
- foul-play input
- Rust `poke-engine` state or IDs

## Result

The full T3-00 inventory is now represented by a typed, reusable Japanese-string module. Applying those constants to the battle screen, dialogs, and Teambuilder remains intentionally deferred so each later task can make narrowly scoped, reviewable text-only JSX changes.
