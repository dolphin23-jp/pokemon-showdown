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
TASK_GUIDE = ROOT / "docs" / "localization" / "phase-1-t1-07-display-name-api.md"
PIN_FILE = ROOT / "config" / "pokemon-showdown-client.json"
LAUNCHER = ROOT / "scripts" / "launcher-server.js"
CLIENT_HELPER = ROOT / "scripts" / "pinned-client-preload.js"
BUILD_CHECK = ROOT / "scripts" / "check-built-client.py"
DOCKERFILE = ROOT / "Dockerfile"
RENDER = ROOT / "render.yaml"
T1_05_MERGE = "72d861147333739363cdb3210ff014ba418ab178"

MANDATORY_TESTS = [
    "scripts/test-foul-play-local-login.py",
    "scripts/test-foul-play-battle-fallbacks.py",
    "scripts/smoke-bss-battle.py",
    "scripts/smoke-bss-faint-recovery.py",
]

DISPLAY_NAME_FUNCTIONS = [
    "displaySpeciesName",
    "displayMoveName",
    "displayAbilityName",
    "displayItemName",
]

PROTECTED_BOUNDARIES = [
    "data/",
    "sim/",
    "/choose",
    "/team",
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
    if commit == upstream_base:
        raise AssertionError("T1-07 must pin a fork revision after the upstream base")

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
            "Phase 1 T1-07",
            "/opt/pokemon-showdown-client",
            "/client.html",
            "/showdown",
            '/updatesettings {"language":"japanese"}',
            "window.PSDisplayNames",
            "window.BattleJapaneseDisplayNames",
            "canonical English",
            "commit_date",
            "upstream_base_commit",
            "X-Pokemon-Showdown-Client-Source: pinned-local",
            "docker build --no-cache --tag pokemon-showdown-ai:localization-check .",
            "python3 scripts/check-pinned-client.py --verify-remote",
            "python3 scripts/check-localization-docs.py",
            T1_05_MERGE,
            *MANDATORY_TESTS,
            *DISPLAY_NAME_FUNCTIONS,
            *PROTECTED_BOUNDARIES,
            *RENDER_ENV_KEYS,
        ],
    )
    require_markers(
        TASK_GUIDE,
        [
            "# Phase 1 T1-07: display-only Japanese name API skeleton",
            commit,
            upstream_base,
            "window.PSDisplayNames",
            "window.BattleJapaneseDisplayNames",
            "canonical English Dex name",
            "mutates_ids: false",
            "protocol_safe: true",
            "T1-08",
            *MANDATORY_TESTS,
            *DISPLAY_NAME_FUNCTIONS,
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
        '"play.pokemonshowdown.com/js/battle-display-names.js"',
        '"PSDisplayNames"',
        '"BattleJapaneseDisplayNames"',
        '"canonical-english-name"',
        '"mutates_ids": False',
        '"protocol_safe": True',
        *[f'"{function}"' for function in DISPLAY_NAME_FUNCTIONS],
    ]:
        if marker not in build_check:
            raise AssertionError(f"Display-name artifact verification is missing: {marker}")

    dockerfile = read(DOCKERFILE)
    for marker in [
        "FROM node:22-bookworm AS client-builder",
        "npm --prefix /client run build",
        "COPY --from=client-builder /client /opt/pokemon-showdown-client",
        "ENV PINNED_CLIENT_ROOT=/opt/pokemon-showdown-client",
    ]:
        if marker not in dockerfile:
            raise AssertionError(f"Docker client build no longer matches the guide: {marker}")

    render = read(RENDER)
    for key in RENDER_ENV_KEYS:
        if f"- key: {key}" not in render:
            raise AssertionError(f"Documented Render environment key is missing from render.yaml: {key}")
    if "healthCheckPath: /health" not in render:
        raise AssertionError("Render health check no longer matches the guide")

    links = {
        str(README.relative_to(ROOT)): verify_local_links(README),
        str(GUIDE.relative_to(ROOT)): verify_local_links(GUIDE),
        str(TASK_GUIDE.relative_to(ROOT)): verify_local_links(TASK_GUIDE),
    }

    return {
        "task": "Phase 1 T1-07",
        "guide": str(GUIDE.relative_to(ROOT)),
        "task_guide": str(TASK_GUIDE.relative_to(ROOT)),
        "readme": str(README.relative_to(ROOT)),
        "pinned_client_commit": commit,
        "upstream_base_commit": upstream_base,
        "runtime_delivery_changed": pin["runtime_delivery_changed"],
        "display_name_api": {
            "api_global": "PSDisplayNames",
            "data_global": "BattleJapaneseDisplayNames",
            "functions": DISPLAY_NAME_FUNCTIONS,
            "fallback": "canonical-english-name",
            "mutates_ids": False,
            "protocol_safe": True,
        },
        "mandatory_tests_documented": MANDATORY_TESTS,
        "protected_boundaries_documented": PROTECTED_BOUNDARIES,
        "local_links_checked": links,
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
