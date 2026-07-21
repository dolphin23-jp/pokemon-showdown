#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
CLIENT_COMMIT = "80c72741b52e91d35ee778982a936ea42526c078"
FOUL_PLAY_COMMIT = "25c976f05cbf2880eaa579afd6db1dcb2c3b57c6"
PROTECTED_PREFIXES = ("data/", "sim/")

REQUIRED_FILES = [
    "Dockerfile",
    ".github/workflows/render-smoke.yml",
    "README.md",
    "docs/localization/README.md",
    "docs/localization/phase-1-t1-07-display-name-api.md",
    "docs/localization/phase-1-t1-08-generated-name-maps.md",
    "docs/localization/phase-1-t1-09-battle-controls.md",
    "docs/localization/phase-1-t1-10-protocol-invariants.md",
    "docs/localization/phase-1-t1-11-foul-play-input-invariants.md",
    "config/pokemon-showdown-client.json",
    "scripts/check-built-client.py",
    "scripts/check-localization-docs.py",
    "scripts/check-pinned-client.py",
    "scripts/launcher-server.js",
    "scripts/pinned-client-preload.js",
    "scripts/patch-foul-play-raw-receive-log.py",
    "scripts/test-foul-play-raw-receive-log.py",
    "scripts/smoke-bss-foul-play-input-invariants.py",
    "scripts/test-japanese-protocol-invariants.js",
    "scripts/smoke-bss-protocol-invariants.py",
    "scripts/smoke-bss-battle.py",
    "scripts/smoke-bss-faint-recovery.py",
    "scripts/test-foul-play-local-login.py",
    "scripts/test-foul-play-battle-fallbacks.py",
]


def read(path: pathlib.Path) -> str:
    if not path.is_file():
        raise AssertionError(f"Required Phase 1 file is missing: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def require_markers(path: pathlib.Path, markers: list[str]) -> None:
    content = read(path)
    missing = [marker for marker in markers if marker not in content]
    if missing:
        raise AssertionError(
            f"{path.relative_to(ROOT)} is missing Phase 1 markers: {missing}"
        )


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
    for candidate in (f"origin/{base_ref}", base_ref):
        try:
            output = run_git("diff", "--name-only", f"{candidate}...HEAD")
        except subprocess.CalledProcessError:
            continue
        return [line for line in output.splitlines() if line]
    raise RuntimeError(f"Could not resolve base ref: {base_ref}")


def build_report(base_ref: str | None) -> dict[str, Any]:
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError(f"Missing Phase 1 files: {missing}")

    pin = json.loads(read(ROOT / "config" / "pokemon-showdown-client.json"))
    if pin.get("commit") != CLIENT_COMMIT:
        raise AssertionError("T1-11 must preserve the T1-09 client commit")
    if pin.get("runtime_delivery_changed") is not True:
        raise AssertionError("The pinned local client must remain active")

    require_markers(
        ROOT / "docs" / "localization" / "README.md",
        [
            "Phase 1 T1-11",
            "FOUL_PLAY_RAW_RECEIVE_LOG",
            "species・moves・abilities・items",
            "T1-11: foul-play受信ログ不変テスト",
            "T1-12: Rust AI境界のIDテスト",
            "T1-13: Phase 1統合回帰",
        ],
    )
    require_markers(
        ROOT / "docs" / "localization" / "phase-1-t1-11-foul-play-input-invariants.md",
        [
            "# Phase 1 T1-11: foul-play raw input invariance tests",
            "exact return value of `websocket.recv()`",
            "species, moves, abilities, and items",
            "bss-foul-play-input-invariant-diagnostics",
        ],
    )
    require_markers(
        ROOT / "scripts" / "patch-foul-play-raw-receive-log.py",
        [
            "PERSONAL_SERVER_RAW_RECEIVE_LOG",
            "FOUL_PLAY_RAW_RECEIVE_LOG",
            '"message": message',
            "return message",
        ],
    )
    require_markers(
        ROOT / "scripts" / "test-foul-play-raw-receive-log.py",
        [
            "Phase 1 T1-11",
            "exact_frame_preserved",
            "default_runtime_unchanged",
        ],
    )
    require_markers(
        ROOT / "scripts" / "smoke-bss-foul-play-input-invariants.py",
        [
            "Phase 1 T1-11",
            "battle_messages",
            "inspect_bot_requests",
            "bot_received_japanese_names",
            '"species": set()',
            '"moves": set()',
            '"abilities": set()',
            '"items": set()',
        ],
    )
    require_markers(
        ROOT / "Dockerfile",
        [
            "scripts/patch-foul-play-raw-receive-log.py",
            "scripts/test-foul-play-raw-receive-log.py",
            "scripts/smoke-bss-foul-play-input-invariants.py",
            FOUL_PLAY_COMMIT,
        ],
    )
    require_markers(
        ROOT / ".github" / "workflows" / "render-smoke.yml",
        [
            "Exercise foul-play raw input invariants",
            "Require foul-play input invariants",
            "bss-foul-play-input-invariant-diagnostics",
            "FOUL_PLAY_RAW_RECEIVE_LOG=/app/.runtime/foul-play-received.jsonl",
            "Exercise raw WebSocket protocol invariants",
            "Exercise BSS battle with captured protocol",
            "Exercise faint and forced-switch recovery",
            "Capture iPad-sized pinned-client baseline",
        ],
    )
    require_markers(
        ROOT / "scripts" / "launcher-server.js",
        [
            "const { handlePinnedClient } = require('./pinned-client-preload');",
            "proxyShowdownRequest(req, res);",
        ],
    )
    require_markers(
        ROOT / "scripts" / "pinned-client-preload.js",
        [
            "const CLIENT_ENTRY = '/client.html';",
            "prefix: '/showdown'",
            "language: 'japanese'",
        ],
    )

    diff_files = changed_files(base_ref)
    protected_changes = [
        path for path in diff_files if path.startswith(PROTECTED_PREFIXES)
    ]
    if protected_changes:
        raise AssertionError(
            "Phase 1 must not modify data/ or sim/: " + ", ".join(protected_changes)
        )

    commit = os.environ.get("GITHUB_SHA")
    if not commit:
        try:
            commit = run_git("rev-parse", "HEAD")
        except (subprocess.CalledProcessError, FileNotFoundError):
            commit = "unknown"

    return {
        "phase": "Phase 1",
        "task": "T1-11",
        "commit": commit,
        "base_ref": base_ref or "",
        "changed_files": diff_files,
        "protected_paths_changed": protected_changes,
        "pinned_client_commit": CLIENT_COMMIT,
        "foul_play_commit": FOUL_PLAY_COMMIT,
        "foul_play_input_invariants": {
            "raw_capture_opt_in": True,
            "exact_receive_value_preserved": True,
            "live_battle_required": True,
            "battle_room_scoped": True,
            "categories": ["species", "moves", "abilities", "items"],
            "japanese_names_allowed": False,
        },
        "required_regression_tests": [
            "scripts/test-foul-play-raw-receive-log.py",
            "scripts/smoke-bss-foul-play-input-invariants.py",
            "scripts/test-japanese-protocol-invariants.js",
            "scripts/smoke-bss-protocol-invariants.py",
            "scripts/test-foul-play-local-login.py",
            "scripts/test-foul-play-battle-fallbacks.py",
            "scripts/smoke-bss-battle.py",
            "scripts/smoke-bss-faint-recovery.py",
        ],
        "next_defined_tasks": [
            "T1-12 Rust AI boundary ID tests",
            "T1-13 Phase 1 integration regression",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify and record the Phase 1 T1-11 localization baseline."
    )
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
