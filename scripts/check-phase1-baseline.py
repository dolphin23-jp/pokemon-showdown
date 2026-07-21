#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "Dockerfile",
    ".gitmodules",
    "scripts/launcher-server.js",
    "scripts/smoke-bss-battle.py",
    "scripts/smoke-bss-faint-recovery.py",
    "scripts/test-foul-play-local-login.py",
    "scripts/test-foul-play-battle-fallbacks.py",
    "translations/japanese/main.ts",
    "translations/japanese/core-commands.ts",
    "translations/japanese/helptickets.ts",
    "translations/japanese/minor-activities.ts",
    "translations/japanese/repeats.ts",
]

LAUNCHER_MARKERS = [
    "const OFFICIAL_CLIENT_HOST = 'play.pokemonshowdown.com';",
    "path: '/testclient-new.html'",
    "location.href = '/client.html';",
    "prefix: '/showdown'",
    "ps.send('/trn ' + cleaned + ',0,');",
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


def build_report(base_ref: str | None) -> dict[str, Any]:
    missing_files = [path for path in REQUIRED_FILES if not (ROOT / path).is_file()]
    if missing_files:
        raise AssertionError(f"Missing baseline files: {missing_files}")

    assert_contains(ROOT / "scripts/launcher-server.js", LAUNCHER_MARKERS)
    assert_contains(ROOT / ".gitmodules", ["url = https://github.com/pmariglia/foul-play.git"])
    assert_contains(
        ROOT / "Dockerfile",
        [
            "git -C foul-play checkout 25c976f05cbf2880eaa579afd6db1dcb2c3b57c6",
            ".venv/bin/python scripts/test-foul-play-local-login.py",
            ".venv/bin/python scripts/test-foul-play-battle-fallbacks.py",
        ],
    )

    diff_files = changed_files(base_ref)
    protected_changes = [
        path for path in diff_files
        if path.startswith(PROTECTED_PREFIXES)
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
        "task": "T1-00",
        "commit": commit,
        "base_ref": base_ref or "",
        "changed_files": diff_files,
        "protected_paths_changed": protected_changes,
        "current_client_delivery": {
            "html_source": "https://play.pokemonshowdown.com/testclient-new.html",
            "static_assets": "proxied from play.pokemonshowdown.com",
            "battle_server_prefix": "/showdown",
            "browser_login_command": "/trn <name>,0,",
        },
        "pinned_dependencies": {
            "foul_play_commit": "25c976f05cbf2880eaa579afd6db1dcb2c3b57c6",
        },
        "required_regression_tests": [
            "scripts/smoke-bss-battle.py",
            "scripts/smoke-bss-faint-recovery.py",
            "scripts/test-foul-play-local-login.py",
            "scripts/test-foul-play-battle-fallbacks.py",
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
    parser = argparse.ArgumentParser(description="Verify and record the Phase 1 pre-change baseline.")
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
