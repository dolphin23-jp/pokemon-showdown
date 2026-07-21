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
TASK_GUIDES = {
    "T1-07": ROOT / "docs" / "localization" / "phase-1-t1-07-display-name-api.md",
    "T1-08": ROOT / "docs" / "localization" / "phase-1-t1-08-generated-name-maps.md",
    "T1-09": ROOT / "docs" / "localization" / "phase-1-t1-09-battle-controls.md",
    "T1-10": ROOT / "docs" / "localization" / "phase-1-t1-10-protocol-invariants.md",
    "T1-11": ROOT / "docs" / "localization" / "phase-1-t1-11-foul-play-input-invariants.md",
    "T1-12": ROOT / "docs" / "localization" / "phase-1-t1-12-poke-engine-id-invariants.md",
}
PIN_FILE = ROOT / "config" / "pokemon-showdown-client.json"
DOCKERFILE = ROOT / "Dockerfile"
WORKFLOW = ROOT / ".github" / "workflows" / "render-smoke.yml"
LAUNCHER = ROOT / "scripts" / "launcher-server.js"
CLIENT_HELPER = ROOT / "scripts" / "pinned-client-preload.js"
RAW_PATCH = ROOT / "scripts" / "patch-foul-play-raw-receive-log.py"
RAW_TEST = ROOT / "scripts" / "test-foul-play-raw-receive-log.py"
RAW_SMOKE = ROOT / "scripts" / "smoke-bss-foul-play-input-invariants.py"
ENGINE_PATCH = ROOT / "scripts" / "patch-foul-play-poke-engine-boundary-log.py"
ENGINE_TEST = ROOT / "scripts" / "test-foul-play-poke-engine-boundary-log.py"
ENGINE_SMOKE = ROOT / "scripts" / "smoke-bss-poke-engine-boundary-invariants.py"
ENGINE_TEAM = ROOT / "config" / "bss-engine-boundary-bot.txt"
SERVER_FIXTURE = ROOT / "scripts" / "test-japanese-protocol-invariants.js"
SERVER_SMOKE = ROOT / "scripts" / "smoke-bss-protocol-invariants.py"

CLIENT_COMMIT = "80c72741b52e91d35ee778982a936ea42526c078"
UPSTREAM_BASE = "085dfabd9bc53c730ac459edf5c28088677adfc2"
FOUL_PLAY_COMMIT = "25c976f05cbf2880eaa579afd6db1dcb2c3b57c6"
DISPLAY_SOURCE_COMMIT = "227b573712414a86ba299d322fa398fbb2893edc"
TARGET_IDS = ["pikachu", "thunderbolt", "static", "lightball"]

PROTECTED_BOUNDARIES = [
    "data/",
    "sim/",
    "|request|",
    "|switch|",
    "|move|",
    "/choose",
    "/team",
    "Team Import/Export",
    "poke-engine",
]


def read(path: pathlib.Path) -> str:
    if not path.is_file():
        raise AssertionError(f"Required file is missing: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def require_markers(path: pathlib.Path, markers: list[str]) -> None:
    content = read(path)
    missing = [marker for marker in markers if marker not in content]
    if missing:
        raise AssertionError(
            f"{path.relative_to(ROOT)} is missing required markers: {missing}"
        )


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
            raise AssertionError(f"Local link escapes the repository: {target}") from error
        if not candidate.exists():
            raise AssertionError(
                f"Broken local link in {path.relative_to(ROOT)}: {target}"
            )
        checked.append(str(candidate.relative_to(ROOT)))
    return sorted(set(checked))


def build_report() -> dict[str, Any]:
    pin = json.loads(read(PIN_FILE))
    if pin.get("commit") != CLIENT_COMMIT:
        raise AssertionError("T1-12 must keep the T1-09 client commit unchanged")
    if pin.get("upstream_base_commit") != UPSTREAM_BASE:
        raise AssertionError("The pinned client upstream base changed unexpectedly")
    if pin.get("runtime_delivery_changed") is not True:
        raise AssertionError("The pinned local client must remain the default delivery")

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
            "Phase 1 T1-12",
            "FOUL_PLAY_RAW_RECEIVE_LOG",
            "FOUL_PLAY_POKE_ENGINE_BOUNDARY_LOG",
            "PokeEngineState.from_string(state)",
            "monte_carlo_tree_search(poke_engine_state",
            "bss-poke-engine-boundary-invariant-diagnostics",
            CLIENT_COMMIT,
            UPSTREAM_BASE,
            FOUL_PLAY_COMMIT,
            DISPLAY_SOURCE_COMMIT,
            *TARGET_IDS,
            *PROTECTED_BOUNDARIES,
        ],
    )

    previous_markers = {
        "T1-07": ["window.PSDisplayNames", "mutates_ids: false", "protocol_safe: true"],
        "T1-08": ["window.BattleJapaneseDisplayNames", DISPLAY_SOURCE_COMMIT, "language ID `11`"],
        "T1-09": ["MutationObserver", "data-cmd", "data-tooltip", "display_text_only: true"],
        "T1-10": ["duplicate the same canonical battle input", "scripts/smoke-bss-protocol-invariants.py"],
        "T1-11": ["FOUL_PLAY_RAW_RECEIVE_LOG", "exact return value of `websocket.recv()`", "baseAbility"],
    }
    for task, markers in previous_markers.items():
        require_markers(TASK_GUIDES[task], markers)

    require_markers(
        TASK_GUIDES["T1-12"],
        [
            "# Phase 1 T1-12: Rust poke-engine ID boundary invariants",
            "PokeEngineState.from_string(state)",
            "monte_carlo_tree_search(poke_engine_state",
            "FOUL_PLAY_POKE_ENGINE_BOUNDARY_LOG",
            "serialized_state",
            "rust_state",
            "bss-poke-engine-boundary-invariant-diagnostics",
            *TARGET_IDS,
            FOUL_PLAY_COMMIT,
            *PROTECTED_BOUNDARIES,
        ],
    )

    require_markers(
        RAW_PATCH,
        ["PERSONAL_SERVER_RAW_RECEIVE_LOG", "FOUL_PLAY_RAW_RECEIVE_LOG", '"message": message', "return message"],
    )
    require_markers(RAW_TEST, ["Phase 1 T1-11", "exact_frame_preserved", "default_runtime_unchanged"])
    require_markers(
        RAW_SMOKE,
        ["Phase 1 T1-11", "inspect_bot_requests", "bot_received_japanese_names", "|request|", "|switch|", "|move|"],
    )

    require_markers(
        ENGINE_PATCH,
        [
            "PERSONAL_SERVER_POKE_ENGINE_BOUNDARY_LOG",
            'os.environ.get("FOUL_PLAY_POKE_ENGINE_BOUNDARY_LOG")',
            '"serialized_state": serialized_state',
            '"rust_state": poke_engine_state.to_string()',
            '"snapshot": _poke_engine_state_snapshot(poke_engine_state)',
            "PokeEngineState.from_string(state)",
            "monte_carlo_tree_search(poke_engine_state",
            "compile(patched",
        ],
    )
    require_markers(
        ENGINE_TEST,
        [
            "Phase 1 T1-12",
            "serialized_state_round_trip",
            "default_runtime_unchanged",
            "japanese_ids_allowed",
            *TARGET_IDS,
        ],
    )
    require_markers(
        ENGINE_SMOKE,
        [
            "Phase 1 T1-12",
            "FOUL_PLAY_POKE_ENGINE_BOUNDARY_LOG",
            "inspect_boundary_records",
            "serialized_state != rust_state",
            "No Rust boundary state preserved pikachu/thunderbolt/static/lightball together",
            "rust_boundary_contains_japanese_names",
            "EngineBoundaryBot",
            *TARGET_IDS,
        ],
    )
    require_markers(
        ENGINE_TEAM,
        ["Pikachu @ Light Ball", "Ability: Static", "- Thunderbolt"],
    )

    require_markers(
        SERVER_FIXTURE,
        ["Phase 1 T1-10", "raw_protocol_unchanged", "choose_command_unchanged"],
    )
    require_markers(
        SERVER_SMOKE,
        ["Phase 1 T1-10", "raw |request| protocol", "outbound /choose command"],
    )
    require_markers(
        DOCKERFILE,
        [
            "scripts/patch-foul-play-poke-engine-boundary-log.py",
            "scripts/test-foul-play-poke-engine-boundary-log.py",
            "scripts/smoke-bss-poke-engine-boundary-invariants.py",
            "config/bss-engine-boundary-bot.txt",
            "python3 scripts/patch-foul-play-poke-engine-boundary-log.py",
            ".venv/bin/python scripts/test-foul-play-poke-engine-boundary-log.py",
            FOUL_PLAY_COMMIT,
        ],
    )
    require_markers(
        WORKFLOW,
        [
            "Start poke-engine boundary container",
            "FOUL_PLAY_POKE_ENGINE_BOUNDARY_LOG=/app/.runtime/poke-engine-boundary.jsonl",
            "Exercise Rust poke-engine ID boundary invariants",
            "Require Rust poke-engine ID boundary invariants",
            "bss-poke-engine-boundary-invariant-diagnostics",
            "/tmp/poke-engine-boundary.jsonl",
            "scripts/smoke-bss-poke-engine-boundary-invariants.py",
            "Exercise foul-play raw input invariants",
            "Exercise raw WebSocket protocol invariants",
            "Exercise BSS battle with captured protocol",
            "Exercise faint and forced-switch recovery",
            "Capture iPad-sized pinned-client baseline",
        ],
    )
    require_markers(
        LAUNCHER,
        ["const { handlePinnedClient } = require('./pinned-client-preload');", "proxyShowdownRequest(req, res);"],
    )
    require_markers(
        CLIENT_HELPER,
        [
            "const CLIENT_ENTRY = '/client.html';",
            "ps.send('/updatesettings ' + JSON.stringify({ language: 'japanese' }));",
            "'x-pokemon-showdown-client-source': 'pinned-local'",
        ],
    )

    links = {
        str(README.relative_to(ROOT)): verify_local_links(README),
        str(GUIDE.relative_to(ROOT)): verify_local_links(GUIDE),
    }
    for task, path in TASK_GUIDES.items():
        links[str(path.relative_to(ROOT))] = verify_local_links(path)

    return {
        "task": "Phase 1 T1-12",
        "guide": str(GUIDE.relative_to(ROOT)),
        "task_guide": str(TASK_GUIDES["T1-12"].relative_to(ROOT)),
        "pinned_client_commit": CLIENT_COMMIT,
        "upstream_base_commit": UPSTREAM_BASE,
        "foul_play_commit": FOUL_PLAY_COMMIT,
        "runtime_delivery_changed": True,
        "poke_engine_boundary_invariants": {
            "patch": str(ENGINE_PATCH.relative_to(ROOT)),
            "unit_test": str(ENGINE_TEST.relative_to(ROOT)),
            "live_smoke": str(ENGINE_SMOKE.relative_to(ROOT)),
            "team": str(ENGINE_TEAM.relative_to(ROOT)),
            "capture_is_opt_in": True,
            "audit_point": "after State.from_string and before MCTS",
            "serialized_state_round_trip_required": True,
            "normalized_ids": TARGET_IDS,
            "japanese_names_allowed": False,
        },
        "t1_10_and_t1_11_retained": True,
        "protected_boundaries": PROTECTED_BOUNDARIES,
        "local_links_checked": links,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify Japanese localization operations documentation and T1-12 contracts."
    )
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
