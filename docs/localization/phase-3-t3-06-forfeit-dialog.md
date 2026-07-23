# Phase 3 T3-06: 降参ダイアログの日本語化

Client merge `9a33ce3117db5dce3ce2b67bcb88c783038c2352` applies the typed `ForfeitDialogJA` strings to the battle-forfeit confirmation dialog.

The T3-08 preflight returned two defects to T3-06:

- client merge `5f48c7d13402abbb3f0c63ba4cd51b29d46234b7` localizes the existing `Cancel` control with `SharedChromeJA.cancel`
- client merge `df2a790caa1f361221df99e55642c19ba16d6f35` explicitly loads `/js/forfeit-dialog-ja.js?` in `index-new.html`, because this client compiles TypeScript files independently rather than bundling side-effect imports

## Display

The dialog now displays:

- `対戦を降参すると負けになります。よろしいですか？`
- `降参して閉じる`
- `降参する`
- `キャンセル`

The adapter is loaded after `client-ui-ja-strings.js` and `panel-popups.js`, before `client-endload.js`. It observes newly rendered popups and scopes all replacements to the already identified forfeit-dialog container.

## Protected behavior

The following command values are unchanged:

- `/closeand /inopener /closeand /forfeit`
- `/closeand /inopener /forfeit`
- `/close`

The implementation changes only text nodes. It preserves the original buttons, icons, event delegation, `/forfeit` execution path, battle protocol, IDs, `/choose`, and `/team` behavior.

## Validation

The client repository's standard Node.js CI passed on both follow-up heads. This includes the client build, TypeScript checking, ESLint with zero warnings, and all existing and new Node tests.

Dedicated regression tests verify every visible forfeit-dialog control, all three unchanged command values, and the explicit browser script order.
