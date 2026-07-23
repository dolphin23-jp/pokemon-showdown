# Phase 3 T3-02: Battle-text coverage for move templates

## Status

T3-02 is complete in the pinned client revision `2bdd5ec95c10bdb107feccb44b05d26a1630a6a6`.

The client implementation modifies only:

- `play.pokemonshowdown.com/src/battle-text-ja.js`

It adds every remaining runtime BattleText template defined by server `data/text/moves.ts` after T3-01.

## Coverage result

T3-02 added 302 templates across 188 move namespaces.

The committed post-T3-01 inventory contained 322 entries. Detailed inspection separated them into:

| Classification | Entries |
| --- | ---: |
| Runtime BattleText strings translated in T3-02 | 302 |
| Nested `champions` ruleset metadata objects | 20 |
| **Inventory entries reviewed** | **322** |

The 20 `champions` entries contain move-description metadata such as `desc` and `shortDesc`. They are not strings consumed by `BattleTextParser` and therefore must not be added to `JAPANESE_BATTLE_TEXT`. The inventory generator now excludes non-generation nested metadata objects while continuing to flatten actual `gen*` BattleText variants.

After this correction and the client translation update, the BattleText inventory contains zero missing runtime templates.

## Translation invariants

For every one of the 302 added templates:

- the namespace and key come from the committed T3-01 inventory and `data/text/moves.ts`
- BattleText aliases are resolved before placeholder comparison, including same-namespace aliases such as `#.start`
- placeholder type, order, and count exactly match the resolved English template
- no pre-existing Japanese entry is overwritten or changed
- dynamic move names continue to use `[MOVE]` and the existing display-name replacement path
- normalized move IDs and simulator data remain canonical English

The implementation does not modify:

- `data/` or `sim/`
- species, move, ability, or item IDs
- WebSocket battle protocol
- `/choose` or `/team`
- `data-cmd` or `data-tooltip`
- Team Import/Export
- foul-play or Rust `poke-engine` inputs

## Validation

The following checks passed for the client implementation:

- exact 302-key target-set validation
- classification of the expected 20 `champions` metadata false positives
- exact placeholder-sequence validation for all translated entries
- comparison proving all pre-T3-02 Japanese entries remained unchanged
- corrected inventory regeneration with zero missing BattleText keys
- existing `test/battle-text-japanese.js`
- full client Node.js test suite

## Inventory regeneration

The server pins the completed client revision in `config/pokemon-showdown-client.json`. With that client checked out next to the server repository, regenerate and verify the inventory with:

```bash
node scripts/generate-phase3-battle-text-inventory.mjs \
  --client-root ../pokemon-showdown-client

node scripts/generate-phase3-battle-text-inventory.mjs \
  --client-root ../pokemon-showdown-client \
  --check
```

The expected result is `0 missing keys` and an empty `byNamespace` object.
