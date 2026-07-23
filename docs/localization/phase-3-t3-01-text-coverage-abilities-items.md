# Phase 3 T3-01: Battle-text coverage for abilities, items, and field effects

## Status

T3-01 is complete in the pinned client revision `7b73bc607d1ca1018e59a37c0f581b1f4649b93e`.

The client implementation modifies only:

- `play.pokemonshowdown.com/src/battle-text-ja.js`

It adds the missing BattleText templates identified by T3-00 whose source namespaces are defined by server `data/text/default.ts`, `data/text/abilities.ts`, or `data/text/items.ts`. Move-only templates from `data/text/moves.ts` remain for T3-02.

## Coverage result

T3-01 added 130 templates across 109 namespaces:

| Source | Added templates |
| --- | ---: |
| `data/text/default.ts` | 1 |
| `data/text/abilities.ts` | 104 |
| `data/text/items.ts` | 25 |
| **Total** | **130** |

After regeneration, the BattleText inventory contains 322 remaining missing templates. All 322 are outside the T3-01 source set and are reserved for T3-02.

Representative completed gaps include:

- `leftovers.heal`
- `disguise.block`
- `disguise.transform`
- weather-suppression messages for `airlock` and `cloudnine`
- Ruin ability activation messages
- Protosynthesis and Quark Drive activation, stat, and end messages
- held-item recovery, activation, recoil, and forced-switch messages

## Translation invariants

The implementation was generated from the committed T3-00 inventory and validated against the English source templates after resolving BattleText aliases such as `#damp` and `#magiccoat`.

For every added key:

- placeholder type, order, and count are identical to the resolved English template
- no pre-existing Japanese key is overwritten
- the entry is stored directly in the canonical `JAPANESE_BATTLE_TEXT` object
- normalized species, move, ability, and item IDs remain unchanged
- protocol, `/choose`, `/team`, Team Import/Export, `data-cmd`, and `data-tooltip` remain unchanged

## Validation

The following checks passed on the client implementation:

- exact 130-key target-set validation
- exact placeholder sequence validation
- comparison proving all pre-T3-01 Japanese entries remained unchanged
- T3-00 inventory regeneration with zero remaining T3-01-category gaps
- expected remaining inventory size of 322 move-only templates
- existing `test/battle-text-japanese.js`
- full client Node.js CI

## Inventory regeneration

The server pins the completed client revision in `config/pokemon-showdown-client.json`. With that client checked out next to the server repository, regenerate the current inventory with:

```bash
node scripts/generate-phase3-battle-text-inventory.mjs \
  --client-root ../pokemon-showdown-client
```

The T3-00 generator no longer assumes that its original sentinel gaps must remain untranslated. This allows the same generator to remain the authoritative coverage check for T3-01, T3-02, and later upstream updates.
