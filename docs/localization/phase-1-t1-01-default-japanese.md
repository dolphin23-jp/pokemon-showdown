# Phase 1 T1-01: default Japanese server language

T1-01 enables the existing server-side Japanese translation dictionaries for browser users opened through the private launcher.

## Browser login sequence

The launcher-injected client code now follows this order:

1. wait for the Showdown client user model and challenge string
2. send `/trn <saved name>,0,`
3. wait until the server confirms the name and `user.named` becomes true
4. send `/updatesettings {"language":"japanese"}` once for that user model
5. stop the polling timer

The language command is deliberately not sent before login confirmation. A client that is already named skips `/trn` and only applies the language setting.

## Scope

This setting affects server-generated translatable messages such as command responses and help text. It does not translate the client UI, battle text templates, Pokémon names, move names, abilities, or items.

## Protected interfaces

T1-01 does not change:

- `data/` or `sim/`
- normalized English IDs
- battle protocol messages
- `/choose`, `/team`, or team Import/Export
- the foul-play login sequence
- the raw protocol received by foul-play
- IDs serialized into the Rust `poke-engine`

The foul-play login test continues to require its exact existing command: `/trn FoulPlayAI,0,`.

## Verification

- `scripts/test-launcher-japanese-language.js` executes the injected login code with a fake client model and checks ordering, one-time delivery, and already-named behavior.
- `scripts/smoke-bss-battle.py` enables Japanese on a real local Showdown connection and requires `/language` to return the translated phrase beginning `現在、Pokémon Showdownを` before starting its normal battle smoke test.
- The existing foul-play and faint-recovery tests remain required.
