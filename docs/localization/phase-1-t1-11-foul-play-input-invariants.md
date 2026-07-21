# Phase 1 T1-11: foul-play raw input invariance tests

T1-11 verifies the exact WebSocket text frames received by foul-play during a real battle. It extends the T1-10 server-side protocol check across the process boundary into the Bot itself.

The acceptance condition is strict: Japanese Pokémon names, move names, ability names, and item names must not reach foul-play's inbound battle data.

## Scope

T1-11 adds:

- an opt-in patch that records the exact return value of `websocket.recv()` in foul-play
- a focused unit test proving the recorded frame and returned frame are identical
- a live BSS smoke test that challenges the real `FoulPlayAI` process
- inspection of only the records appended after the test starts
- inspection of only frames belonging to the test battle room
- category coverage for species, moves, abilities, and items
- a dedicated GitHub Actions diagnostic artifact

T1-11 does not add another translated UI surface and does not change the pinned client revision.

## Raw receive instrumentation

`scripts/patch-foul-play-raw-receive-log.py` patches the pinned foul-play file:

```text
foul-play/fp/websocket_client.py
```

Immediately after:

```python
message = await self.websocket.recv()
```

it optionally appends one JSONL record containing:

```json
{"received_at_ns": 0, "message": "<exact inbound WebSocket text frame>"}
```

Recording is enabled only when this environment variable is set:

```text
FOUL_PLAY_RAW_RECEIVE_LOG
```

Without that variable, no file is opened and foul-play behaves as before. The return value from `receive_message()` is never replaced or normalized.

The JSON representation is a storage envelope. After JSON decoding, the `message` value must be byte-equivalent as UTF-8 text to the inbound WebSocket frame.

## Focused instrumentation test

`scripts/test-foul-play-raw-receive-log.py` uses a fake WebSocket and verifies:

- the exact multiline battle frame is returned unchanged
- one JSONL record is written when the environment variable is present
- the decoded `message` is exactly equal to the inbound frame
- an integer nanosecond timestamp is present
- no new record is written when the environment variable is absent

The fixture includes canonical English examples from all four categories:

- species: `Calyrex-Shadow`
- move: `Astral Barrage` / `astralbarrage`
- ability: `asonespectrier`
- item: `choicespecs`

## Live foul-play input smoke

`scripts/smoke-bss-foul-play-input-invariants.py` performs a real battle against `FoulPlayAI` in:

```text
gen9nationaldexallgenerationsbss
```

The challenger first enables Japanese server settings and confirms the Japanese `/language` response. This proves that localization is active somewhere in the same server session while the Bot boundary remains canonical.

The smoke test records the current raw-log byte offset before issuing the challenge. It then:

1. uploads the fixed smoke opponent team
2. challenges `FoulPlayAI`
3. submits `/team 123456`
4. submits the first legal `/choose move <index>`
5. waits until the first move is observed
6. reads only JSONL records appended after the saved offset
7. filters only frames containing the exact battle room
8. parses Bot-side `|request|`, `|switch|`, and `|move|` lines
9. verifies species, move, ability, and item coverage
10. rejects any Japanese character in the battle-scoped Bot input
11. forfeits after the invariant has been proven

## Category checks

The Bot-side `|request|` data must contain non-empty values for:

| Category | Fields inspected |
| --- | --- |
| species | `ident`, `details`, and `|switch|` details |
| moves | active `move`, active `id`, side `moves`, and `|move|` name |
| abilities | side `baseAbility` |
| items | side `item` |

Move names and IDs must retain the canonical relationship:

```text
toID(move name) == move id
```

The test rejects Japanese Hiragana, Katakana, half-width Katakana, and CJK characters anywhere in the battle-scoped raw frames. This is stronger than checking only a short list of known translations.

## CI integration

The Docker build:

- syntax-checks the patch, unit test, and smoke test
- applies the patch to pinned foul-play revision `25c976f05cbf2880eaa579afd6db1dcb2c3b57c6`
- runs `scripts/test-foul-play-raw-receive-log.py`

Render smoke starts the main test container with:

```text
FOUL_PLAY_RAW_RECEIVE_LOG=/app/.runtime/foul-play-received.jsonl
```

It runs T1-11 before the T1-10 protocol smoke and uploads:

- `bss-foul-play-input-invariants.log`
- `bss-foul-play-input-invariants.status`
- `foul-play-received.jsonl`

under the artifact:

```text
bss-foul-play-input-invariant-diagnostics
```

The existing T1-10 protocol smoke, normal BSS smoke, post-faint recovery smoke, access-gate checks, fixed-client checks, and iPad-sized captures remain mandatory.

## Protected boundaries

T1-11 must not change:

- `data/`
- `sim/`
- normalized species, move, ability, or item IDs
- `|request|`
- `|switch|`
- `|move|`
- `/choose`
- `/team`
- Team Import/Export
- challenge format IDs
- the content returned from foul-play `receive_message()`
- the data passed onward toward Rust `poke-engine`

The raw audit file is test instrumentation only. It is disabled by default and must not become a new runtime protocol or translation source.

## Completion condition

T1-11 is complete only when:

- the opt-in raw receive patch is applied safely to the pinned foul-play source
- exact-frame and default-disabled unit tests pass
- a live battle produces Bot-side `|request|`, `|switch|`, and `|move|` records
- species, moves, abilities, and items are all covered
- no Japanese name or Japanese character reaches the Bot-side battle frames
- T1-10 and all earlier regression tests continue to pass
- Node.js CI, localization documentation CI, Docker build, Render smoke, access checks, and browser captures all pass
