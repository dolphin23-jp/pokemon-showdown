# Phase 3 T3-05: 対戦画面クロームへの適用

T3-05 applies the T3-04 `BattleChromeJA` and `SharedChromeJA` framework directly to `play.pokemonshowdown.com/src/panel-battle.tsx` in client merge `e6e7b0fb18531d53db583a28850cc52a537d166b` (client PR #13).

The T3-08 preflight found one directly rendered label outside the original inventory scan: `Timer`. Client follow-up merge `9584cf3102b4f3ec4e36521d8374f466a037febb` adds typed `BattleChromeJA.timer` and renders `タイマー` without changing timer behavior.

## Applied scope

The battle list, spectator filters, replay controls, player move and switch controls, team preview, timer, post-battle actions, and request notifications now render through the typed Japanese constants. The implementation includes `対戦`, `交代`, `チーム`, `キャンセル`, `タイマー`, `アニメーションをスキップ`, `メインメニュー`, `再戦`, `中央へ移動`, `現在の選出`, the spectator username placeholder and search button, and the request-notification titles and bodies.

Seven source strings discovered while applying and auditing dynamic battle UI were added to `BattleChromeSources`: the three notification bodies, the opponent label, the lead label, the numbered-slot template, and the timer label.

## Protected boundaries

The client application passes compared the complete ordered `data-cmd` and `data-tooltip` attribute lists before and after substitution. No component state, event handlers, timer countdown logic, protocol values, normalized IDs, `/choose`, `/team`, Team Import/Export, `data/`, or `sim/` behavior changed.

## Regression coverage

The client AST test follows `BattleChromeJA` and `SharedChromeJA` references in the applied file while continuing to compare them with the complete framework. After the timer follow-up it verifies 326 UI occurrences and 234 unique English source strings. The full client build, TypeScript, ESLint, and Node.js suite passed on the merged client head.

The server inventory generator resolves the same applied references from `client-ui-ja-strings.ts`, so the committed Phase 3 inventory remains reproducible after direct JSX substitution.

## Browser evidence

The dedicated `Japanese battle chrome live smoke` workflow serves the clean pinned client, feeds raw canonical battle protocol and real request JSON into the real `BattlePanel`, operates the battle/switch/team/cancel controls, verifies Japanese visible text with unchanged command attributes, and captures 1280×900 PNG evidence for move choice, team preview, and post-battle controls.
