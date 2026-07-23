# Phase 3 T3-08: Phase 3統合回帰

T3-08 is the final read-only integration gate for T3-00 through T3-07. It does not alter battle, Teambuilder, protocol, command, ID, or simulator behavior. Defects found during preflight are returned to their original tasks before this gate is allowed to pass.

## Preflight corrections

The integration preflight returned three visible defects to their original tasks:

- T3-05: the directly rendered `Timer` label was localized as `タイマー`.
- T3-06: the remaining forfeit-dialog `Cancel` control was localized as `キャンセル` while preserving `data-cmd="/close"`.
- T3-06: the compiled forfeit adapter was explicitly loaded by `index-new.html`, because this client compiles TypeScript files independently rather than bundling side-effect imports.

T3-08 begins only after those corrected client revisions are pinned by the server.

## Integration workflow

`.github/workflows/phase3-integration-regression.yml` performs the complete gate on one pull-request head:

1. run the pinned client build, TypeScript, ESLint, and Node regression suite;
2. perform a Docker `--no-cache` clean build;
3. execute the T3-03 BattleText coverage checker and require `totalMissing: 0`;
4. compare the Phase 3 server and client baselines with the final heads;
5. require no `data/` or `sim/` changes;
6. require the ordered `data-cmd` and `data-tooltip` inventories to remain identical in all Phase 3 target files;
7. run the existing canonical protocol and command invariant test;
8. serve the Docker-built pinned client and operate the real browser UI;
9. run the existing Japanese Teambuilder browser smoke, including the English Import/Export boundary;
10. wait for the existing Localization documentation, Node.js CI, Render smoke test, Phase 1 integration regression, and Phase 3 baseline inventory workflows on the same head;
11. generate and validate the final Phase 3 JSON report.

The pre-existing Japanese battle chrome live smoke also runs independently on the same pull request and must be green before merge. Its browser harness now waits for the mounted battle model and uses a page-installed click helper; these are verification-only changes and do not alter the client runtime.

After the pinned client regression suite completes, its checkout is moved to the runner's temporary directory. The Docker `--no-cache` build therefore receives the same clean server-only context as a normal production build, while the relocated client Git history remains available for the later boundary and coverage audits.

Browser fixture requests are passed to the mounted `BattleRoom` through its existing `receiveLine(['request', json])` path. This avoids re-splitting an already serialized JSON fixture; the canonical WebSocket battle protocol itself remains covered by the independent protocol invariant test and is not changed.

## Battle browser evidence

The browser flow captures 1280×900 screenshots for:

- battle start;
- switching Pokémon;
- move use and a canonical English `Leftovers` protocol effect rendered in Japanese;
- the Japanese forfeit confirmation dialog;
- the final win/loss view.

The test clicks the real switch, move, and forfeit controls and verifies canonical outbound commands. It asserts the three original `/forfeit` and `/close` command values without modifying them.

## Teambuilder browser evidence

The existing real Teambuilder flow creates and edits a team through the UI and captures:

- the Japanese construction editor;
- the English Team Import/Export view.

Visible species, ability, item, move, and Phase 3 editor labels are Japanese. Model values, packed-team contents, search entry values, and Import/Export text remain canonical English.

## Protected boundaries

The final audit requires all of the following:

- no server `data/` changes;
- no server `sim/` changes;
- no client data-table or simulator changes;
- no species, move, ability, or item ID changes;
- no WebSocket battle-protocol localization;
- no `/choose`, `/team`, or `/forfeit` behavior changes;
- no `data-cmd` or `data-tooltip` changes;
- Team Import/Export remains English.

## Final report

The workflow writes `docs/localization/phase-3-integration-regression.json`. It may set:

```json
{
  "phase": "Phase 3",
  "phase3_complete": true
}
```

only when every completion criterion is true and all seven screenshot files have valid PNG signatures, exact 1280×900 dimensions, byte sizes, and SHA-256 hashes.
