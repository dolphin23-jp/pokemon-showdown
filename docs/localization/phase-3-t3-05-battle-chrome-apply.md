# Phase 3 T3-05: Japanese battle chrome application

## Status

T3-05 is implemented in the pinned client revision `0e5715cc325796752d07e7ecd3fdd175ad8fc52b`.

The client imports `BattleChromeJA` and `SharedChromeJA` from `play.pokemonshowdown.com/src/client-ui-ja-strings.ts` and applies them directly to every Phase 3 inventory entry owned by `play.pokemonshowdown.com/src/panel-battle.tsx`.

## Applied surface

The direct JSX/property substitutions cover:

- the public battle list, including `vs.`, close/refresh controls, format and Elo filters, the spectator username search placeholder and search button
- battle request notifications for team preview, move choice, and switching
- playback controls, including play, pause, first/previous/next/end navigation, viewpoint switching, and turn navigation
- move, switch, target, and team-preview controls
- `Battle`, `Switch`, `Team`, `Cancel`, `Skip`, `Skip animation`, `Move to center`, and `Team so far`
- replay download/upload controls
- ended-battle `Replay`, `Main menu`, and `Rematch` controls

Six static English sources that were assembled dynamically and therefore were not represented as standalone rows in the original T3-00 JSX inventory were added to the T3-04 framework during application:

- `Move in your battle`
- `Switch in your battle`
- `Choose your team order in your battle`
- `Opponent:`
- `lead`
- `slot ${…}`

Notification bodies place the opponent name in a natural Japanese suffix such as `（対戦相手：FoulPlayAI）`; no protocol player name is translated or rewritten.

## Inventory traceability

After T3-05, `panel-battle.tsx` no longer contains the original hard-coded English literals. The server and client AST inventory checks therefore resolve references such as:

```tsx
<强>{BattleChromeJA.battleTab}</强>
<button data-cmd="/cancel">{SharedChromeJA.cancel}</button>
```

back to the exact English source strings stored in the `*Sources` objects. This preserves one authoritative inventory while allowing later tasks to continue scanning the not-yet-applied dialog and Teambuilder files.

The complete framework now contains 233 unique English/Japanese pairs and represents 325 inventory occurrences across the six Phase 3 source files.

## Command and protocol boundaries

T3-05 changes rendered strings only. In particular, it preserves:

- every `data-cmd`, including `/movemenu`, `/switchmenu`, `/shift`, `/cancel`, `/move`, and `/switch`
- every `data-tooltip`
- component conditions, event handlers, request handling, and state management
- normalized species, move, ability, item, and format IDs
- raw WebSocket battle protocol and `|request|` JSON
- `/choose` and `/team`
- Team Import/Export
- `data/` and `sim/`
- foul-play input
- Rust `poke-engine` state and IDs

The client test compares all `data-cmd` and `data-tooltip` attributes before and after the scripted application and requires exact equality. The existing Phase 1 battle-control tests continue to require Japanese visible move/Pokémon names while canonical command payloads remain English.

## Live browser verification

The server adds:

```text
scripts/smoke-japanese-battle-chrome.mjs
.github/workflows/japanese-battle-chrome.yml
```

The workflow clean-builds the Docker image with the pinned client, starts the local server and foul-play bot, opens the real client in headless Chrome at 1280 × 900, and performs a real battle through the client.

It verifies all of the following:

1. the battle-list spectator search displays `ユーザー名（前方一致）` and `検索`
2. team preview displays `チーム` and `先発を選択`
3. the team-preview notification title is `選出してください`
4. the battle and switch controls display `対戦` and `交代` while retaining `/movemenu` and `/switchmenu`
5. clicking the battle control opens the move menu
6. clicking the switch control opens the switch menu
7. choosing a move exposes a Japanese `キャンセル` control that retains `/cancel`, and clicking it restores the move request
8. the move notification title is `技を選んでください`
9. the packed team sent to the server remains canonical English
10. after forfeiting, `リプレイ`, `メインメニュー`, and `再戦` are displayed

The workflow uploads a JSON report, browser logs, server diagnostics, and five screenshots in the `japanese-battle-chrome-live-evidence` artifact:

- battle list
- team preview
- move menu
- switch menu
- ended battle

## Result

All `panel-battle.tsx` entries from the Phase 3 UI chrome inventory are rendered through `BattleChromeJA` or `SharedChromeJA`. The client build, TypeScript, ESLint, Node.js tests, Phase 1 battle-control tests, inventory equality checks, and live browser command checks form the T3-05 completion gate.
