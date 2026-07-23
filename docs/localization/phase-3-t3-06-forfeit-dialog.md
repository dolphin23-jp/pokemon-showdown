# Phase 3 T3-06: 降参ダイアログの日本語化

Client merge `9a33ce3117db5dce3ce2b67bcb88c783038c2352` applies the existing typed `ForfeitDialogJA` strings to the battle-forfeit confirmation dialog.

## Display

The dialog now displays:

- `対戦を降参すると負けになります。よろしいですか？`
- `降参して閉じる`
- `降参する`

The adapter is loaded from `client-endload.ts`, observes newly rendered popups, and scopes itself to the two exact existing forfeit-button command attributes.

## Protected behavior

The following command values are unchanged:

- `/closeand /inopener /closeand /forfeit`
- `/closeand /inopener /forfeit`

The implementation changes only text nodes. It preserves the original buttons, icons, event delegation, `/forfeit` execution path, battle protocol, IDs, `/choose`, and `/team` behavior.

## Validation

The client repository's standard Node.js CI passed on the final pull-request head. This includes the client build, TypeScript checking, ESLint with zero warnings, and the existing Node test suite.
