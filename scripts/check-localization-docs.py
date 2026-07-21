#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pathlib
import re
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
GUIDE = ROOT / "docs" / "localization" / "README.md"
T1_07_GUIDE = ROOT / "docs" / "localization" / "phase-1-t1-07-display-name-api.md"
T1_08_GUIDE = ROOT / "docs" / "localization" / "phase-1-t1-08-generated-name-maps.md"
T1_09_GUIDE = ROOT / "docs" / "localization" / "phase-1-t1-09-battle-controls.md"
TASK_GUIDE = ROOT / "docs" / "localization" / "phase-1-t1-10-protocol-invariants.md"
PIN_FILE = ROOT / "config" / "pokemon-showdown-client.json"
LAUNCHER = ROOT / "scripts" / "launcher-server.js"
CLIENT_HELPER = ROOT / "scripts" / "pinned-client-preload.js"
BUILD_CHECK = ROOT / "scripts" / "check-built-client.py"
PROTOCOL_FIXTURE = ROOT / "scripts" / "test-japanese-protocol-invariants.js"
PROTOCOL_SMOKE = ROOT / "scripts" / "smoke-bss-protocol-invariants.py"
DOCKERFILE = ROOT / "Dockerfile"
RENDER = ROOT / "render.yaml"
RENDER_SMOKE = ROOT / ".github" / "workflows" / "render-smoke.yml"
T1_05_MERGE = "72d861147333739363cdb3210ff014ba418ab178"
T1_08_CLIENT = "523a5fb38255916f6fb7bcd4b5b3ccaa5414f6eb"
T1_09_CLIENT = "80c72741b52e91d35ee778982a936ea42526c078"
DISPLAY_NAME_SOURCE_REPOSITORY = "PokeAPI/pokeapi"
DISPLAY_NAME_SOURCE_COMMIT = "227b573712414a86ba299d322fa398fbb2893edc"
DISPLAY_NAME_LANGUAGE_ID = 11

EXISTING_REGRESSION_TESTS = [
    "scripts/test-foul-play-local-login.py",
    "scripts/test-foul-play-battle-fallbacks.py",
    "scripts/smoke-bss-battle.py",
    "scripts/smoke-bss-faint-recovery.py",
]

T1_10_TESTS = [
    "scripts/test-japanese-protocol-invariants.js",
    "scripts/smoke-bss-protocol-invariants.py",
]

DISPLAY_NAME_FUNCTIONS = [
    "displaySpeciesName",
    "displayMoveName",
    "displayAbilityName",
    "displayItemName",
]

BATTLE_CONTROL_SELECTORS = [
    "button.movebutton",
    'button[data-tooltip^="switchpokemon|"]',
    'button[data-tooltip^="allypokemon|"]',
    'button[data-tooltip^="activepokemon|"]',
]

CRITICAL_PROTOCOL = [
    "|request|",
    "|switch|",
    "|move|",
    "/choose",
    "/team",
]

PROTECTED_BOUNDARIES = [
    "data/",
    "sim/",
    *CRITICAL_PROTOCOL,
    "Import/Export",
    "foul-play",
    "poke-engine",
]

RENDER_ENV_KEYS = [
    "ACCESS_TOKEN",
    "DEFAULT_PLAYER_NAME",
    "FOUL_PLAY_USERNAME",
    "FOUL_PLAY_FORMAT",
]

MINIMUM_COUNTS = {
    "species": 1000,
    "moves": 800,
    "abilities": 250,
    "items": 1500,
}


def read(path: pathlib.Path) -> str:
    if not path.is_file():
        raise AssertionError(f"Required documentation input is missing: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def require_markers(path: pathlib.Path, markers: list[str]) -> None:
    content = read(path)
    missing = [marker for marker in markers if marker not in content]
    if missing:
        raise AssertionError(f"{path.relative_to(ROOT)} is missing documentation markers: {missing}")


def verify_local_links(path: pathlib.Path) -> list[str]:
    content = read(path)
    checked: list[str] = []
    for target in re.findall(r"\]\(([^)]+)\)", content):
        target = target.strip()
        if not target or target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        relative = target.split("#", 1)[0]
        candidate = (path.parent / relative).resolve()
        try:
            candidate.relative_to(ROOT)
        except ValueError as error:
            raise AssertionError(f"Local link escapes the repository: {path}: {target}") from error
        if not candidate.exists():
            raise AssertionError(f"Broken local link in {path.relative_to(ROOT)}: {target}")
        checked.append(str(candidate.relative_to(ROOT)))
    return sorted(set(checked))


def build_report() -> dict[str, Any]:
    pin = json.loads(read(PIN_FILE))
    if pin.get("runtime_delivery_changed") is not True:
        raise AssertionError("The operations guide is valid only after the T1-05 local-client cutover")
    commit = str(pin.get("commit", ""))
    upstream_base = str(pin.get("upstream_base_commit", ""))
    for name, value in (("commit", commit), ("upstream_base_commit", upstream_base)):
        if not re.fullmatch(r"[0-9a-f]{40}", value):
            raise AssertionError(f"The pinned client {name} must be a full lowercase SHA")
    if commit != T1_09_CLIENT:
        raise AssertionError("T1-10 must keep the T1-09 pinned client revision unchanged")
    if commit == upstream_base:
        raise AssertionError("The pinned client must remain after the upstream base")

    require_markers(
        README,
        [
            "Personal AI deployment and Japanese localization",
            "[docs/localization/README.md](./docs/localization/README.md)",
            "Japanese names and text are display-only",
        ],
    )
    require_markers(
        GUIDE,
        [
            "# Japanese localization operations",
            "Phase 1 T1-10",
            "/opt/pokemon-showdown-client",
            "/client.html",
            "/showdown",
            '/updatesettings {"language":"japanese"}',
            "window.PSDisplayNames",
            "window.BattleJapaneseDisplayNames",
            "canonical English",
            "battle-display-names.meta.json",
            DISPLAY_NAME_SOURCE_REPOSITORY,
            DISPLAY_NAME_SOURCE_COMMIT,
            "language ID `11`",
            "MutationObserver",
            "data-cmd",
            "data-tooltip",
            "display_text_only: true",
            "mutates_commands: false",
            "mutates_tooltips: false",
            "preserves_unknown_names: true",
            "複製入力テスト",
            "実WebSocketテスト",
            "raw `|request|`",
            "raw `|switch|`",
            "raw `|move|`",
            T1_08_CLIENT,
            T1_09_CLIENT,
            "X-Pokemon-Showdown-Client-Source: pinned-local",
            "docker build --no-cache --tag pokemon-showdown-ai:localization-check .",
            "python3 scripts/check-pinned-client.py --verify-remote",
            "python3 scripts/check-localization-docs.py",
            T1_05_MERGE,
            *EXISTING_REGRESSION_TESTS,
            *T1_10_TESTS,
            *DISPLAY_NAME_FUNCTIONS,
            *BATTLE_CONTROL_SELECTORS,
            *PROTECTED_BOUNDARIES,
            *RENDER_ENV_KEYS,
            *[f"{name} {count}" for name, count in MINIMUM_COUNTS.items()],
        ],
    )

    require_markers(
        T1_07_GUIDE,
        [
            "# Phase 1 T1-07: display-only Japanese name API skeleton",
            "window.PSDisplayNames",
            "window.BattleJapaneseDisplayNames",
            "canonical English Dex name",
            "mutates_ids: false",
            "protocol_safe: true",
        ],
    )
    require_markers(
        T1_08_GUIDE,
        [
            "# Phase 1 T1-08: mechanically generated Japanese display-name maps",
            DISPLAY_NAME_SOURCE_REPOSITORY,
            DISPLAY_NAME_SOURCE_COMMIT,
            "language ID `11`",
            "window.BattleJapaneseDisplayNames",
            "battle-display-names.meta.json",
            "canonical English Dex name",
            "mutates_ids: false",
            "protocol_safe: true",
        ],
    )
    require_markers(
        T1_09_GUIDE,
        [
            "# Phase 1 T1-09: Japanese battle choice controls",
            T1_09_CLIENT,
            upstream_base,
            "MutationObserver",
            "data-cmd",
            "data-tooltip",
            "display_text_only: true",
            "mutates_commands: false",
            "mutates_tooltips: false",
            "preserves_unknown_names: true",
            "mutates_ids: false",
            "protocol_safe: true",
        ],
    )
    require_markers(
        TASK_GUIDE,
        [
            "# Phase 1 T1-10: server protocol invariance tests",
            "duplicate the same canonical battle input",
            "byte-for-byte canonical English",
            "scripts/test-japanese-protocol-invariants.js",
            "scripts/smoke-bss-protocol-invariants.py",
            "10まんボルト",
            "ピカチュウ",
            "Japanese `/language` response",
            "bss-protocol-invariant-diagnostics",
            *EXISTING_REGRESSION_TESTS,
            *T1_10_TESTS,
            *CRITICAL_PROTOCOL,
            *PROTECTED_BOUNDARIES,
        ],
    )

    launcher = read(LAUNCHER)
    for marker in [
        "const { handlePinnedClient } = require('./pinned-client-preload');",
        "if (handlePinnedClient(req, res)) return;",
        "proxyShowdownRequest(req, res);",
    ]:
        if marker not in launcher:
            raise AssertionError(f"Launcher architecture no longer matches the guide: {marker}")
    for retired in ["OFFICIAL_CLIENT_HOST", "servePatchedClient", "'official-client'"]:
        if retired in launcher:
            raise AssertionError(f"Retired official runtime path returned: {retired}")

    client_helper = read(CLIENT_HELPER)
    for marker in [
        "const CLIENT_ENTRY = '/client.html';",
        "const CLIENT_ROOT = path.resolve(process.env.PINNED_CLIENT_ROOT || '/opt/pokemon-showdown-client');",
        "ps.send('/trn ' + cleaned + ',0,');",
        "ps.send('/updatesettings ' + JSON.stringify({ language: 'japanese' }));",
        "'x-pokemon-showdown-client-source': 'pinned-local'",
    ]:
        if marker not in client_helper:
            raise AssertionError(f"Pinned client architecture no longer matches the guide: {marker}")

    build_check = read(BUILD_CHECK)
    for marker in [
        '"config/japanese-display-name-api.json"',
        '"play.pokemonshowdown.com/src/battle-display-names.ts"',
        '"play.pokemonshowdown.com/js/battle-display-names.js"',
        '"play.pokemonshowdown.com/js/battle-display-names.meta.json"',
        '"PSDisplayNames"',
        '"BattleJapaneseDisplayNames"',
        '"canonical-english-name"',
        '"display_text_only": True',
        '"mutates_commands": False',
        '"mutates_tooltips": False',
        '"preserves_unknown_names": True',
        '"mutates_ids": False',
        '"protocol_safe": True',
        "localizeBattleControlButton",
        "MutationObserver",
        DISPLAY_NAME_SOURCE_REPOSITORY,
        DISPLAY_NAME_SOURCE_COMMIT,
        *[f'"{function}"' for function in DISPLAY_NAME_FUNCTIONS],
        *BATTLE_CONTROL_SELECTORS,
        *[f'"{name}": {count}' for name, count in MINIMUM_COUNTS.items()],
    ]:
        if marker not in build_check:
            raise AssertionError(f"Display-name artifact verification is missing: {marker}")

    require_markers(
        PROTOCOL_FIXTURE,
        [
            "Phase 1 T1-10",
            "raw WebSocket protocol changed during display rendering",
            "|request| JSON changed during display rendering",
            "|switch|p1a: Pikachu|Pikachu, L50|100/100",
            "|move|p1a: Pikachu|Thunderbolt|p2a: Charizard",
            "/choose move 1",
            "10まんボルト",
            "ピカチュウ",
            "raw_protocol_unchanged",
            "request_json_unchanged",
            "choose_command_unchanged",
        ],
    )
    require_markers(
        PROTOCOL_SMOKE,
        [
            "Phase 1 T1-10",
            "verify_japanese_translations",
            "raw |request| protocol",
            "raw |switch| protocol",
            "raw |move| protocol",
            "outbound /choose command",
            "outbound /team command",
            "choose_command_unchanged",
            "raw_protocol_contains_japanese_display_names",
            "|/choose move ",
            "|/team 123456",
        ],
    )

    dockerfile = read(DOCKERFILE)
    for marker in [
        "FROM node:22-bookworm AS client-builder",
        "npm --prefix /client run build",
        "COPY --from=client-builder /client /opt/pokemon-showdown-client",
        "ENV PINNED_CLIENT_ROOT=/opt/pokemon-showdown-client",
        "scripts/test-japanese-protocol-invariants.js",
        "scripts/smoke-bss-protocol-invariants.py",
        "node scripts/test-japanese-protocol-invariants.js",
    ]:
        if marker not in dockerfile:
            raise AssertionError(f"Docker T1-10 verification is missing: {marker}")

    workflow = read(RENDER_SMOKE)
    for marker in [
        "Verify duplicate protocol and rendered-text invariants",
        "Exercise raw WebSocket protocol invariants",
        "Require raw protocol invariants",
        "bss-protocol-invariant-diagnostics",
        "/tmp/protocol-render-invariants.json",
        "/tmp/bss-protocol-invariants.log",
        "scripts/test-japanese-protocol-invariants.js",
        "scripts/smoke-bss-protocol-invariants.py",
    ]:
        if marker not in workflow:
            raise AssertionError(f"Render smoke T1-10 coverage is missing: {marker}")

    render = read(RENDER)
    for key in RENDER_ENV_KEYS:
        if f"- key: {key}" not in render:
            raise AssertionError(f"Documented Render environment key is missing from render.yaml: {key}")
    if "healthCheckPath: /health" not in render:
        raise AssertionError("Render health check no longer matches the guide")

    links = {
        str(README.relative_to(ROOT)): verify_local_links(README),
        str(GUIDE.relative_to(ROOT)): verify_local_links(GUIDE),
        str(T1_07_GUIDE.relative_to(ROOT)): verify_local_links(T1_07_GUIDE),
        str(T1_08_GUIDE.relative_to(ROOT)): verify_local_links(T1_08_GUIDE),
        str(T1_09_GUIDE.relative_to(ROOT)): verify_local_links(T1_09_GUIDE),
        str(TASK_GUIDE.relative_to(ROOT)): verify_local_links(TASK_GUIDE),
    }

    return {
        "task": "Phase 1 T1-10",
        "guide": str(GUIDE.relative_to(ROOT)),
        "task_guide": str(TASK_GUIDE.relative_to(ROOT)),
        "previous_task_guides": [
            str(T1_07_GUIDE.relative_to(ROOT)),
            str(T1_08_GUIDE.relative_to(ROOT)),
            str(T1_09_GUIDE.relative_to(ROOT)),
        ],
        "readme": str(README.relative_to(ROOT)),
        "pinned_client_commit": commit,
        "upstream_base_commit": upstream_base,
        "runtime_delivery_changed": pin["runtime_delivery_changed"],
        "protocol_invariants": {
            "fixture_test": str(PROTOCOL_FIXTURE.relative_to(ROOT)),
            "live_websocket_test": str(PROTOCOL_SMOKE.relative_to(ROOT)),
            "critical_protocol": CRITICAL_PROTOCOL,
            "duplicates_input_before_rendering": True,
            "rendered_text_may_be_japanese": True,
            "raw_protocol_must_remain_english": True,
            "request_json_must_remain_unchanged": True,
            "choose_command_must_remain_unchanged": True,
        },
        "display_name_api": {
            "api_global": "PSDisplayNames",
            "data_global": "BattleJapaneseDisplayNames",
            "functions": DISPLAY_NAME_FUNCTIONS,
            "fallback": "canonical-english-name",
            "source_repository": DISPLAY_NAME_SOURCE_REPOSITORY,
            "source_commit": DISPLAY_NAME_SOURCE_COMMIT,
            "language_id": DISPLAY_NAME_LANGUAGE_ID,
            "minimum_counts": MINIMUM_COUNTS,
            "battle_controls": {
                "selectors": BATTLE_CONTROL_SELECTORS,
                "translated_categories": ["moves", "species"],
                "display_text_only": True,
                "mutates_commands": False,
                "mutates_tooltips": False,
                "preserves_unknown_names": True,
            },
            "mutates_ids": False,
            "protocol_safe": True,
        },
        "existing_regression_tests_documented": EXISTING_REGRESSION_TESTS,
        "t1_10_tests_documented": T1_10_TESTS,
        "protected_boundaries_documented": PROTECTED_BOUNDARIES,
        "local_links_checked": links,
        "rollback_client": T1_08_CLIENT,
        "current_client": T1_09_CLIENT,
        "rollback_anchor": T1_05_MERGE,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify the Japanese localization operations documentation.")
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()

    report = build_report()
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")


if __name__ == "__main__":
    main()
