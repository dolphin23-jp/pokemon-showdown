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
TARGET_IDS = ["pikachu", "thunderbolt", "static", "lightball"]

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
    "docs/localization/phase-1-t1-12-poke-engine-id-invariants.md",
    "docs/localization/phase-1-t1-13-integration-regression.md",
    "config/pokemon-showdown-client.json",
    "config/bss-engine-boundary-bot.txt",
    "scripts/audit-phase1-integration.py",
    "scripts/check-built-client.py",
    "scripts/check-localization-docs.py",
    "scripts/check-pinned-client.py",
    "scripts/launcher-server.js",
    "scripts/pinned-client-preload.js",
    "scripts/patch-foul-play-raw-receive-log.py",
    "scripts/test-foul-play-raw-receive-log.py",
    "scripts/smoke-bss-foul-play-input-invariants.py",
    "scripts/patch-foul-play-poke-engine-boundary-log.py",
    "scripts/test-foul-play-poke-engine-boundary-log.py",
    "scripts/smoke-bss-poke-engine-boundary-invariants.py",
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
        raise AssertionError("T1-13 must preserve the T1-09 client commit")
    if pin.get("runtime_delivery_changed") is not True:
        raise AssertionError("The pinned local client must remain active")

    require_markers(
        ROOT / "docs" / "localization" / "README.md",
        [
            "Phase 1 T1-13",
            "Phase 1完了",
            "ready_for_phase2",
            "phase1-integration-regression-report",
            "scripts/audit-phase1-integration.py",
            "FOUL_PLAY_RAW_RECEIVE_LOG",
            "FOUL_PLAY_POKE_ENGINE_BOUNDARY_LOG",
            "PokeEngineState.from_string(state)",
            "monte_carlo_tree_search(poke_engine_state",
            *TARGET_IDS,
        ],
    )
    require_markers(
        ROOT / "docs" / "localization" / "phase-1-t1-13-integration-regression.md",
        [
            "# Phase 1 T1-13: integration regression",
            "Dockerをクリーンビルドして全テスト・ブラウザ確認・成果物監査",
            "phase1-integration-regression.json",
            "phase1-integration-regression-report",
            '"phase1_complete": true',
            '"ready_for_phase2": true',
            "1024 × 1366",
            "Phase 2の具体的タスクは別の計画で定義",
        ],
    )
    require_markers(
        ROOT / "scripts" / "audit-phase1-integration.py",
        [
            "STATUS_FILES",
            "REQUIRED_ARTIFACTS",
            "EXPECTED_SCREENSHOT_SIZE = (1024, 1366)",
            '"task": "T1-13"',
            '"phase1_complete": True',
            '"ready_for_phase2": True',
            "artifact_audit",
            "sha256",
        ],
    )
    require_markers(
        ROOT / "docs" / "localization" / "phase-1-t1-12-poke-engine-id-invariants.md",
        [
            "# Phase 1 T1-12: Rust poke-engine ID boundary invariants",
            "PokeEngineState.from_string(state)",
            "monte_carlo_tree_search(poke_engine_state",
            "FOUL_PLAY_POKE_ENGINE_BOUNDARY_LOG",
            *TARGET_IDS,
        ],
    )
    require_markers(
        ROOT / "scripts" / "patch-foul-play-poke-engine-boundary-log.py",
        [
            "PERSONAL_SERVER_POKE_ENGINE_BOUNDARY_LOG",
            "FOUL_PLAY_POKE_ENGINE_BOUNDARY_LOG",
            '"serialized_state": serialized_state',
            '"rust_state": poke_engine_state.to_string()',
            "PokeEngineState.from_string(state)",
            "monte_carlo_tree_search(poke_engine_state",
            "compile(patched",
        ],
    )
    require_markers(
        ROOT / "scripts" / "smoke-bss-poke-engine-boundary-invariants.py",
        [
            "Phase 1 T1-12",
            "inspect_boundary_records",
            "state_round_trip_exact",
            "rust_boundary_contains_japanese_names",
            "EngineBoundaryBot",
            *TARGET_IDS,
        ],
    )
    require_markers(
        ROOT / "scripts" / "patch-foul-play-raw-receive-log.py",
        ["PERSONAL_SERVER_RAW_RECEIVE_LOG", "FOUL_PLAY_RAW_RECEIVE_LOG", '"message": message', "return message"],
    )
    require_markers(
        ROOT / "scripts" / "smoke-bss-foul-play-input-invariants.py",
        ["Phase 1 T1-11", "inspect_bot_requests", "bot_received_japanese_names"],
    )
    require_markers(
        ROOT / "Dockerfile",
        [
            "scripts/audit-phase1-integration.py",
            "scripts/patch-foul-play-poke-engine-boundary-log.py",
            "scripts/test-foul-play-poke-engine-boundary-log.py",
            "scripts/smoke-bss-poke-engine-boundary-invariants.py",
            "config/bss-engine-boundary-bot.txt",
            FOUL_PLAY_COMMIT,
        ],
    )
    require_markers(
        ROOT / ".github" / "workflows" / "render-smoke.yml",
        [
            "Build Render image with captured output",
            "Verify embedded pinned client build",
            "Verify duplicate protocol and rendered-text invariants",
            "Exercise Rust poke-engine ID boundary invariants",
            "Exercise foul-play raw input invariants",
            "Exercise raw WebSocket protocol invariants",
            "Exercise BSS battle with captured protocol",
            "Exercise faint and forced-switch recovery",
            "Verify access gate and pinned default client",
            "Capture iPad-sized pinned-client baseline",
            "Audit Phase 1 integration artifacts",
            "Require Phase 1 ready for Phase 2",
            "phase1-integration-regression-report",
            "/tmp/phase1-integration-regression.json",
        ],
    )
    require_markers(
        ROOT / "scripts" / "launcher-server.js",
        ["const { handlePinnedClient } = require('./pinned-client-preload');", "proxyShowdownRequest(req, res);"],
    )
    require_markers(
        ROOT / "scripts" / "pinned-client-preload.js",
        ["const CLIENT_ENTRY = '/client.html';", "prefix: '/showdown'", "language: 'japanese'"],
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
        "task": "T1-13",
        "commit": commit,
        "base_ref": base_ref or "",
        "changed_files": diff_files,
        "protected_paths_changed": protected_changes,
        "pinned_client_commit": CLIENT_COMMIT,
        "foul_play_commit": FOUL_PLAY_COMMIT,
        "integration_regression_contract": {
            "clean_docker_build_required": True,
            "all_regression_tests_required": True,
            "browser_verification_required": True,
            "ipad_screenshots_required": [1024, 1366],
            "artifact_hash_manifest_required": True,
            "final_report": "/tmp/phase1-integration-regression.json",
            "artifact_name": "phase1-integration-regression-report",
            "ready_for_phase2_requires_all_conditions": True,
        },
        "required_regression_tests": [
            "scripts/test-foul-play-poke-engine-boundary-log.py",
            "scripts/smoke-bss-poke-engine-boundary-invariants.py",
            "scripts/test-foul-play-raw-receive-log.py",
            "scripts/smoke-bss-foul-play-input-invariants.py",
            "scripts/test-japanese-protocol-invariants.js",
            "scripts/smoke-bss-protocol-invariants.py",
            "scripts/test-foul-play-local-login.py",
            "scripts/test-foul-play-battle-fallbacks.py",
            "scripts/smoke-bss-battle.py",
            "scripts/smoke-bss-faint-recovery.py",
            "scripts/audit-phase1-integration.py",
        ],
        "phase1_final_task": True,
        "phase2_task_defined": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify and record the Phase 1 T1-13 integration baseline."
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
