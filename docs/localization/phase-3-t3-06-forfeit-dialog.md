# Phase 3 T3-06: 降参ダイアログの日本語化

Client merge `9a33ce3117db5dce3ce2b67bcb88c783038c2352` applies the typed `ForfeitDialogJA` strings to the battle-forfeit confirmation dialog.

The T3-08 preflight found that the dialog's existing `Cancel` control was still visible in English. Client follow-up merge `5f48c7d13402abbb3f0c63ba4cd51b29d46234b7` returns that defect to T3-06 and localizes the remaining control with `SharedChromeJA.cancel`.

## Display

The dialog now displays:

- `対戦を降参すると負けになります。よろしいですか？`
- `降参して閉じる`
- `降参する`
- `キャンセル`

The adapter is loaded from `client-endload.ts`, observes newly rendered popups, and scopes all replacements to the already identified forfeit-dialog container.

## Protected behavior

The following command values are unchanged:

- `/closeand /inopener /closeand /forfeit`
- `/closeand /inopener /forfeit`
- `/close`

The implementation changes only text nodes. It preserves the original buttons, icons, event delegation, `/forfeit` execution path, battle protocol, IDs, `/choose`, and `/team` behavior.

## Validation

The client repository's standard Node.js CI passed on the final follow-up head. This includes the client build, TypeScript checking, ESLint with zero warnings, and all existing and new Node tests.

A dedicated regression test verifies every visible forfeit-dialog control and all three unchanged command values.
