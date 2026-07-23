# Phase 3 T3-07: チームビルダー周辺ラベルの日本語化

Client merge `e3de20f1470256f60f777289c7d7e750de844c3f` applies the typed Japanese UI chrome tables to the Teambuilder interface.

Prerequisite client merge `5d12ab2a25b1d1f6b00aabb75457434d30dc1494` loads the compiled UI chrome constants before the panel scripts that consume them.

## Applied files

The localization covers 192 inventoried UI occurrences across:

- `play.pokemonshowdown.com/src/battle-team-editor.tsx`
- `play.pokemonshowdown.com/src/panel-teambuilder.tsx`
- `play.pokemonshowdown.com/src/panel-teambuilder-team.tsx`
- `play.pokemonshowdown.com/src/panel-teamdropdown.tsx`

The implementation uses the existing typed groups:

- `SharedChromeJA`
- `TeambuilderChromeJA`
- `TeambuilderListChromeJA`
- `TeambuilderTeamChromeJA`
- `TeamDropdownChromeJA`

This includes direct JSX text, labels nested inside conditional JSX, and applicable `placeholder` and `title` attributes.

## Protected behavior and scope

The existing `PSDisplayNames` species, move, ability, and item display-name integration was not changed.

The following were preserved unchanged:

- `data-cmd` and `data-tooltip` values
- species, move, ability, and item IDs
- WebSocket battle protocol
- `data/` and `sim/` behavior

Team Import/Export remains intentionally English. This includes:

- the `Import/Export` heading
- the textarea placeholder and contents
- `Back`
- `Save (not allowed for partial exports)`
- `Save changes`
- `Backup`
- the dynamic `search results` and `folder` suffixes

## Validation

The final client head passed the standard Node.js CI, including the complete client build, TypeScript checking, ESLint with zero warnings, and all existing and new Node tests.

Permanent regression tests verify typed Japanese chrome usage in all four target files and verify that the full Team Import/Export UI remains English.

Manual browser screenshots were not produced for this task; automated source-boundary checks and the full client regression suite were used instead.
