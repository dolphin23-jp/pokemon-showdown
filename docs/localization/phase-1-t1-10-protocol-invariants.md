# Phase 1 T1-10: server protocol invariance tests

T1-10 adds regression tests proving that the Japanese localization introduced through T1-01, T1-05, and T1-09 remains display-only.

This task does not add another translated surface and does not change the pinned client revision. It converts the protected protocol boundary into an executable acceptance test.

## Acceptance criteria from the Phase 1 plan

- duplicate the same canonical battle input for protocol inspection and rendered display inspection
- allow rendered move and species text to become Japanese
- require raw WebSocket protocol to remain byte-for-byte canonical English
- require `|request|`, `|switch|`, and `|move|` payloads to remain canonical English
- require the outbound `/choose` command to remain unchanged
- preserve `/team`, normalized IDs, request JSON semantics, foul-play input, and Rust `poke-engine` input

## Deterministic duplicated-input test

`scripts/test-japanese-protocol-invariants.js` loads the pinned client bundle from:

```text
/opt/pokemon-showdown-client/play.pokemonshowdown.com/js/battle-display-names.js
```

The test creates one canonical protocol fixture containing:

```text
|request|{"active":[{"moves":[{"move":"Thunderbolt","id":"thunderbolt"}]}]...}
|switch|p1a: Pikachu|Pikachu, L50|100/100
|move|p1a: Pikachu|Thunderbolt|p2a: Charizard
```

The exact same fixture is retained as the raw protocol copy while its move and species names are used to build synthetic battle choice controls.

The expected split is:

| Layer | Required result |
| --- | --- |
| raw `|request|` | `Thunderbolt`, `thunderbolt`, and `Pikachu` remain unchanged |
| raw `|switch|` | `Pikachu` remains unchanged |
| raw `|move|` | `Thunderbolt` remains unchanged |
| outbound choice | `/choose move 1` remains unchanged |
| move button text | `10まんボルト` |
| species button text | `ピカチュウ` |
| move tooltip | `move|Thunderbolt|0` remains unchanged |
| switch tooltip | `switchpokemon|0` remains unchanged |

The test repeats the display substitution through the T1-09 `MutationObserver` callback and again requires the raw protocol and `/choose` command to remain unchanged.

## Live WebSocket test

`scripts/smoke-bss-protocol-invariants.py` connects to the actual local Pokémon Showdown WebSocket endpoint, claims the name `ProtocolSmoke`, enables Japanese server settings, and confirms the Japanese `/language` response.

It then challenges `FoulPlayAI` in `gen9nationaldexallgenerationsbss` and inspects the actual battle traffic.

The test requires:

- at least one raw `|request|` line
- at least one raw `|switch|` line
- at least one raw `|move|` line
- a canonical `/team 123456` command
- a canonical `/choose move <index>` command
- no Japanese display characters in any critical raw protocol line or outbound battle command
- move IDs in `|request|` to equal the normalized canonical English move name

The battle is forfeited only after all required protocol types and the outbound `/choose` command have been observed.

## Protected boundaries

T1-10 must not change:

- `data/`
- `sim/`
- species, move, ability, or item IDs
- `|request|`
- `|switch|`
- `|move|`
- `/choose`
- `/team`
- Team Import/Export
- challenge format IDs
- foul-play inputs
- Rust `poke-engine` inputs

Japanese strings may appear in server command responses and rendered browser text. They must not appear in the raw battle protocol types or outbound choice commands checked by this task.

## CI integration

The deterministic fixture runs during the Docker build after the pinned client has been copied into the final image. Render smoke runs the fixture a second time as a separately visible step.

The live WebSocket invariant smoke runs after the Bot identity check and before the existing normal-battle and post-faint smoke tests. Its logs and exit status are uploaded as `bss-protocol-invariant-diagnostics`.

The existing tests remain required:

- `scripts/test-foul-play-local-login.py`
- `scripts/test-foul-play-battle-fallbacks.py`
- `scripts/smoke-bss-battle.py`
- `scripts/smoke-bss-faint-recovery.py`

T1-10 adds:

- `node scripts/test-japanese-protocol-invariants.js --client-root /opt/pokemon-showdown-client`
- `.venv/bin/python scripts/smoke-bss-protocol-invariants.py --bot FoulPlayAI --port 8000 --timeout 90`

## Completion condition

T1-10 is complete only when the deterministic fixture, live WebSocket invariant smoke, existing four regression tests, Node.js CI, localization documentation CI, Docker build, pinned-client verification, access-gate checks, and iPad-sized browser capture all pass.
