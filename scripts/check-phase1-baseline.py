#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]

DISPLAY_NAME_SOURCE_REPOSITORY = "PokeAPI/pokeapi"
DISPLAY_NAME_SOURCE_COMMIT = "227b573712414a86ba299d322fa398fbb2893edc"
DISPLAY_NAME_LANGUAGE_ID = 11
DISPLAY_NAME_MINIMUM_COUNTS = {
    "species": 1000,
    "moves": 800,
    "abilities": 250,
    "items": 1500,
}

REQUIRED_FILES = [
    "Dockerfile",
    ".gitmodules",
    "README.md",
    "docs/localization/README.md",
    "docs/localization/phase-1-t1-07-display-name-api.md",
    "docs/localization/phase-1-t1-08-generated-name-maps.md",
    "config/pokemon-showdown-client.json",
    "scripts/check-built-client.py",
    "scripts/check-localization-docs.py",
    "scripts/check-pinned-client.py",
    "scripts/launcher-server.js",
    "scripts/pinned-client-preload.js",
    "scripts/smoke-bss-battle.py",
    "scripts/smoke-bss-faint-recovery.py",
    "scripts/test-launcher-japanese-language.js",
    "scripts/test-launcher-pinned-client.js",
    "scripts/test-foul-play-local-login.py",
    "scripts/test-foul-play-battle-fallbacks.py",
    "translations/japanese/main.ts",
    "translations/japanese/core-commands.ts",
    "translations/japanese/helptickets.ts",
    "translations/japanese/minor-activities.ts",
    "translations/japanese/repeats.ts",
]

LAUNCHER_MARKERS = [
    "const { handlePinnedClient } = require('./pinned-client-preload');",
    "location.href = '/client.html';",
    "if (handlePinnedClient(req, res)) return;",
    "proxyShowdownRequest(req, res);",
    "send(res, 404, 'text/plain; charset=utf-8', 'Not found.');",
]

PINNED_CLIENT_MARKERS = [
    "const CLIENT_ENTRY = '/client.html';",
    "const LOCAL_CLIENT_PREFIX = '/local-client/';",
    "const PUBLIC_PREFIXES = ['/data/', '/js/', '/src/', '/style/'];",
    "prefix: '/showdown'",
    "ps.send('/trn ' + cleaned + ',0,');",
    "ps.send('/updatesettings ' + JSON.stringify({ language: 'japanese' }));",
    "x-pokemon-showdown-client-source",
    "Net.defaultRoute = location.origin;",
]

DOCUMENTATION_MARKERS = [
    "# Japanese localization operations",
    "Phase 1 T1-08",
    "## ロールバック",
    "## 絶対に変えない境界",
    "scripts/check-localization-docs.py",
    "battle-display-names.meta.json",
    DISPLAY_NAME_SOURCE_REPOSITORY,
    DISPLAY_NAME_SOURCE_COMMIT,
]

DISPLAY_NAME_API_MARKERS = [
    "# Phase 1 T1-07: display-only Japanese name API skeleton",
    "window.PSDisplayNames",
    "window.BattleJapaneseDisplayNames",
    "displaySpeciesName",
    "displayMoveName",
    "displayAbilityName",
    "displayItemName",
    "canonical English Dex name",
    "T1-08",
]

GENERATED_NAME_MAP_MARKERS = [
    "# Phase 1 T1-08: mechanically generated Japanese display-name maps",
    "window.BattleJapaneseDisplayNames",
    "species",
    "moves",
    "abilities",
    "items",
    "battle-display-names.meta.json",
    DISPLAY_NAME_SOURCE_REPOSITORY,
    DISPLAY_NAME_SOURCE_COMMIT,
    "language ID `11`",
    "mutates_ids: false",
    "protocol_safe: true",
]

RETIRED_RUNTIME_MARKERS = [
    "const OFFICIAL_CLIENT_HOST = 'play.pokemonshowdown.com';",
    "function servePatchedClient(",
    "proxyRequest(req, res, 'official-client')",
    "https.get(",
]

PROTECTED_PREFIXES = ("data/", "sim/")


def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def changed_files(base_ref: str | None) -> list[str]:
    if not base_ref:
        return []
    candidates = [f"origin/{base_ref}", base_ref]
    for candidate in candidates:
        try:
            output = run_git("diff", "--name-only", f"{candidate}...HEAD")
        except subprocess.CalledProcessError:
            continue
        return [line for line in output.splitlines() if line]
    raise RuntimeError(f"Could not resolve base ref: {base_ref}")


def assert_contains(path: pathlib.Path, markers: list[str]) -> None:
    content = path.read_text(encoding="utf-8")
    missing = [marker for marker in markers if marker not in content]
    if missing:
        raise AssertionError(f"{path.relative_to(ROOT)} is missing markers: {missing}")


def assert_not_contains(path: pathlib.Path, markers: list[str]) -> None:
    content = path.read_text(encoding="utf-8")
    present = [marker for marker in markers if marker in content]
    if present:
        raise AssertionError(f"{path.relative_to(ROOT)} still contains retired markers: {present}")


def build_report(base_ref: str | None) -> dict[str, Any]:
    missing_files = [path for path in REQUIRED_FILES if not (ROOT / path).is_file()]
    if missing_files:
        raise AssertionError(f"Missing baseline files: {missing_files}")

    launcher = ROOT / "scripts" / "launcher-server.js"
    assert_contains(launcher, LAUNCHER_MARKERS)
    assert_not_contains(launcher, RETIRED_RUNTIME_MARKERS)
    assert_contains(ROOT / "scripts/pinned-client-preload.js", PINNED_CLIENT_MARKERS)
    assert_contains(ROOT / "docs/localization/README.md", DOCUMENTATION_MARKERS)
    assert_contains(
        ROOT / "docs/localization/phase-1-t1-07-display-name-api.md",
        DISPLAY_NAME_API_MARKERS,
    )
    assert_contains(
        ROOT / "docs/localization/phase-1-t1-08-generated-name-maps.md",
        GENERATED_NAME_MAP_MARKERS,
    )
    assert_contains(
        ROOT / "README.md",
        [
            "Personal AI deployment and Japanese localization",
            "[docs/localization/README.md](./docs/localization/README.md)",
        ],
    )
    assert_contains(ROOT / ".gitmodules", ["url = https://github.com/pmariglia/foul-play.git"])
    assert_contains(
        ROOT / "Dockerfile",
        [
            "FROM node:22-bookworm AS client-builder",
            "npm --prefix /client ci",
            "npm --prefix /client run build",
            "COPY --from=client-builder /client /opt/pokemon-showdown-client",
            "ENV PINNED_CLIENT_ROOT=/opt/pokemon-showdown-client",
            "node scripts/test-launcher-pinned-client.js",
            "python3 scripts/check-built-client.py",
            "python3 scripts/check-localization-docs.py",
            "node scripts/test-launcher-japanese-language.js",
            "git -C foul-play checkout 25c976f05cbf2880eaa579afd6db1dcb2c3b57c6",
            ".venv/bin/python scripts/test-foul-play-local-login.py",
            ".venv/bin/python scripts/test-foul-play-battle-fallbacks.py",
        ],
    )
    assert_not_contains(ROOT / "Dockerfile", ["NODE_OPTIONS=--require=/app/scripts/pinned-client-preload.js"])

    client_pin = json.loads(
        (ROOT / "config" / "pokemon-showdown-client.json").read_text(encoding="utf-8")
    )
    if client_pin.get("runtime_delivery_changed") is not True:
        raise AssertionError("T1-08 must preserve the completed local-client cutover")
    if client_pin.get("commit") == client_pin.get("upstream_base_commit"):
        raise AssertionError("T1-08 must pin the fork revision containing generated display-name maps")

    build_check = ROOT / "scripts" / "check-built-client.py"
    assert_contains(
        build_check,
        [
            "play.pokemonshowdown.com/js/battle-display-names.meta.json",
            DISPLAY_NAME_SOURCE_REPOSITORY,
            DISPLAY_NAME_SOURCE_COMMIT,
            "DISPLAY_NAME_LANGUAGE_ID = 11",
            *[f'"{name}": {count}' for name, count in DISPLAY_NAME_MINIMUM_COUNTS.items()],
        ],
    )

    diff_files = changed_files(base_ref)
    protected_changes = [
        path for path in diff_files if path.startswith(PROTECTED_PREFIXES)
    ]
    if protected_changes:
        raise AssertionError(
            "Phase 1 baseline must not modify protected data/sim paths: "
            + ", ".join(protected_changes)
        )

    commit = os.environ.get("GITHUB_SHA")
    if not commit:
        try:
            commit = run_git("rev-parse", "HEAD")
        except (subprocess.CalledProcessError, FileNotFoundError):
            commit = "unknown"

    return {
        "phase": "Phase 1",
        "task": "T1-08",
        "commit": commit,
        "base_ref": base_ref or "",
        "changed_files": diff_files,
        "protected_paths_changed": protected_changes,
        "display_name_api": {
            "client_commit": client_pin["commit"],
            "upstream_base_commit": client_pin["upstream_base_commit"],
            "api_global": "PSDisplayNames",
            "data_global": "BattleJapaneseDisplayNames",
            "functions": [
                "displaySpeciesName",
                "displayMoveName",
                "displayAbilityName",
                "displayItemName",
            ],
            "fallback": "canonical-english-name",
            "source_repository": DISPLAY_NAME_SOURCE_REPOSITORY,
            "source_commit": DISPLAY_NAME_SOURCE_COMMIT,
            "language_id": DISPLAY_NAME_LANGUAGE_ID,
            "minimum_counts": DISPLAY_NAME_MINIMUM_COUNTS,
            "generated_metadata": "play.pokemonshowdown.com/js/battle-display-names.meta.json",
            "mutates_ids": False,
            "protocol_safe": True,
            "generated_maps_added": True,
            "implementation_repository": client_pin["fork_repository"],
            "task_document": "docs/localization/phase-1-t1-08-generated-name-maps.md",
            "previous_task_document": "docs/localization/phase-1-t1-07-display-name-api.md",
        },
        "operations_documentation": {
            "authoritative_guide": "docs/localization/README.md",
            "repository_entrypoint": "README.md",
            "machine_verifier": "scripts/check-localization-docs.py",
            "covers": [
                "architecture",
                "client updates",
                "generated display-name map updates",
                "server translation updates",
                "required tests",
                "troubleshooting",
                "rollback",
                "protected protocol and ID boundaries",
            ],
        },
        "current_client_delivery": {
            "html_source": "/opt/pokemon-showdown-client/play.pokemonshowdown.com/testclient-new.html",
            "entry_path": "/client.html",
            "static_sources": ["/data/", "/js/", "/src/", "/style/", "/config/config.js"],
            "official_runtime_html_fetch": False,
            "official_runtime_asset_proxy": False,
            "unknown_paths_return_404": True,
            "battle_server_prefix": "/showdown",
            "browser_login_command": "/trn <name>,0,",
            "browser_language_command": '/updatesettings {"language":"japanese"}',
        },
        "pinned_client_build": {
            "image_path": "/opt/pokemon-showdown-client",
            "build_command": "npm ci && npm run build",
            "manifest": "/opt/pokemon-showdown-client/build-manifest.json",
            "generated_display_name_bundle": "/opt/pokemon-showdown-client/play.pokemonshowdown.com/js/battle-display-names.js",
            "generated_display_name_metadata": "/opt/pokemon-showdown-client/play.pokemonshowdown.com/js/battle-display-names.meta.json",
            "served_by_default": True,
        },
        "legacy_local_alias": {
            "entry_path": "/local-client/testclient-new.html",
            "static_prefix": "/local-client/",
            "kept_for_t1_04_compatibility": True,
        },
        "pinned_dependencies": {
            "foul_play_commit": "25c976f05cbf2880eaa579afd6db1dcb2c3b57c6",
            "pokemon_showdown_client_fork": client_pin["fork_repository"],
            "pokemon_showdown_client_upstream": client_pin["upstream_repository"],
            "pokemon_showdown_client_commit": client_pin["commit"],
            "pokemon_showdown_client_upstream_base": client_pin["upstream_base_commit"],
            "display_name_source_repository": DISPLAY_NAME_SOURCE_REPOSITORY,
            "display_name_source_commit": DISPLAY_NAME_SOURCE_COMMIT,
        },
        "required_regression_tests": [
            "scripts/smoke-bss-battle.py",
            "scripts/smoke-bss-faint-recovery.py",
            "scripts/test-foul-play-local-login.py",
            "scripts/test-foul-play-battle-fallbacks.py",
        ],
        "localization_safety_tests": [
            "scripts/test-launcher-japanese-language.js",
            "scripts/test-launcher-pinned-client.js",
            "Japanese /language response in scripts/smoke-bss-battle.py",
            "scripts/check-pinned-client.py --verify-remote",
            "scripts/check-built-client.py generated-map contract",
            "scripts/check-localization-docs.py",
        ],
        "japanese_server_translation_files": [
            "translations/japanese/main.ts",
            "translations/japanese/core-commands.ts",
            "translations/japanese/helptickets.ts",
            "translations/japanese/minor-activities.ts",
            "translations/japanese/repeats.ts",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify and record the Phase 1 localization baseline.")
    parser.add_argument("--base-ref", default=os.environ.get("GITHUB_BASE_REF") or "")
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()

    report = build_report(args.base_ref or None)
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")


if __name__ == "__main__":
    main()
