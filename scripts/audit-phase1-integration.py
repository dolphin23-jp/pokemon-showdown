#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import struct
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXPECTED_CLIENT_COMMIT = json.loads(
    (ROOT / "config" / "pokemon-showdown-client.json").read_text(encoding="utf-8")
)["commit"]
EXPECTED_SCREENSHOT_SIZE = (1024, 1366)
ALLOW_EMPTY_ARTIFACTS = {"client-traversal.txt"}

STATUS_FILES = {
    "docker_clean_build": "docker-build.status",
    "t1_12_poke_engine_boundary": "bss-poke-engine-boundary-invariants.status",
    "t1_11_foul_play_input": "bss-foul-play-input-invariants.status",
    "t1_10_server_protocol": "bss-protocol-invariants.status",
    "bss_turn_one": "bss-smoke.status",
    "post_faint_recovery": "bss-faint-smoke.status",
}

REQUIRED_ARTIFACTS = (
    "phase1-baseline.json",
    "client-pin.json",
    "docker-build.log",
    "docker-build.status",
    "client-build-verification.json",
    "client-build-manifest.json",
    "protocol-render-invariants.json",
    "bss-poke-engine-boundary-invariants.log",
    "bss-poke-engine-boundary-invariants.status",
    "poke-engine-boundary.jsonl",
    "poke-engine-boundary-report.json",
    "bss-foul-play-input-invariants.log",
    "bss-foul-play-input-invariants.status",
    "foul-play-received.jsonl",
    "bss-protocol-invariants.log",
    "bss-protocol-invariants.status",
    "bss-smoke.log",
    "bss-smoke.status",
    "bss-faint-smoke.log",
    "bss-faint-smoke.status",
    "authenticated-launcher.html",
    "authenticated-client.headers",
    "authenticated-client.html",
    "client-main.headers",
    "client-main.js",
    "client-config.headers",
    "client-config.js",
    "local-client-alias.headers",
    "local-client-alias.html",
    "client-traversal.txt",
    "unknown-path.txt",
    "launcher-baseline.html",
    "client-baseline.html",
    "phase1-launcher-ipad.png",
    "phase1-client-ipad.png",
)


def require_file(root: pathlib.Path, name: str) -> pathlib.Path:
    path = root / name
    if not path.is_file():
        raise AssertionError(f"Required Phase 1 artifact is missing: {name}")
    if path.stat().st_size <= 0 and name not in ALLOW_EMPTY_ARTIFACTS:
        raise AssertionError(f"Required Phase 1 artifact is empty: {name}")
    return path


def read_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"Expected a JSON object: {path.name}")
    return value


def task_report_from_log(path: pathlib.Path, expected_task: str) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    decoder = json.JSONDecoder()
    matches: list[dict[str, Any]] = []
    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            value, _end = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("task") == expected_task:
            matches.append(value)
    if not matches:
        raise AssertionError(
            f"No {expected_task} JSON report was found in {path.name}"
        )
    return matches[-1]


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def png_size(path: pathlib.Path) -> tuple[int, int]:
    with path.open("rb") as stream:
        header = stream.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError(f"Artifact is not a valid PNG header: {path.name}")
    if header[12:16] != b"IHDR":
        raise AssertionError(f"PNG is missing IHDR at the expected position: {path.name}")
    return struct.unpack(">II", header[16:24])


def require_text(
    path: pathlib.Path,
    markers: tuple[str, ...],
    *,
    ignore_case: bool = False,
) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    haystack = text.lower() if ignore_case else text
    missing = [
        marker
        for marker in markers
        if (marker.lower() if ignore_case else marker) not in haystack
    ]
    if missing:
        raise AssertionError(f"{path.name} is missing markers: {missing}")


def require_false(report: dict[str, Any], key: str, source: str) -> None:
    if report.get(key) is not False:
        raise AssertionError(f"{source} must report {key}=false")


def require_true(report: dict[str, Any], key: str, source: str) -> None:
    if report.get(key) is not True:
        raise AssertionError(f"{source} must report {key}=true")


def build_report(root: pathlib.Path) -> dict[str, Any]:
    paths = {name: require_file(root, name) for name in REQUIRED_ARTIFACTS}

    statuses: dict[str, int] = {}
    for label, filename in STATUS_FILES.items():
        raw = paths[filename].read_text(encoding="utf-8").strip()
        try:
            status = int(raw)
        except ValueError as error:
            raise AssertionError(f"Invalid exit status in {filename}: {raw!r}") from error
        if status != 0:
            raise AssertionError(f"Phase 1 regression failed: {label} returned {status}")
        statuses[label] = status

    baseline = read_json(paths["phase1-baseline.json"])
    if baseline.get("phase") != "Phase 1" or baseline.get("task") != "T1-13":
        raise AssertionError("Phase 1 baseline is not finalized at T1-13")
    if baseline.get("protected_paths_changed") != []:
        raise AssertionError("Protected data/ or sim/ paths changed during Phase 1")
    if baseline.get("pinned_client_commit") != EXPECTED_CLIENT_COMMIT:
        raise AssertionError("Integration baseline used an unexpected pinned client commit")

    client_pin = read_json(paths["client-pin.json"])
    if client_pin.get("commit") != EXPECTED_CLIENT_COMMIT:
        raise AssertionError("Remote client pin report does not match the approved commit")
    require_true(client_pin, "remote_verified", "client-pin.json")
    require_true(client_pin, "runtime_delivery_changed", "client-pin.json")

    client_build = read_json(paths["client-build-verification.json"])
    if client_build.get("commit") != EXPECTED_CLIENT_COMMIT:
        raise AssertionError("Embedded client verification used an unexpected commit")
    require_true(client_build, "verified", "client-build-verification.json")
    if int(client_build.get("artifact_count", 0)) < 10:
        raise AssertionError("Embedded client verification reported too few artifacts")

    client_manifest = read_json(paths["client-build-manifest.json"])
    if client_manifest.get("commit") != EXPECTED_CLIENT_COMMIT:
        raise AssertionError("Embedded client manifest used an unexpected commit")
    artifacts = client_manifest.get("artifacts")
    if not isinstance(artifacts, dict) or len(artifacts) < 10:
        raise AssertionError("Embedded client manifest is incomplete")
    display_api = client_manifest.get("display_name_api")
    if not isinstance(display_api, dict):
        raise AssertionError("Embedded client manifest is missing the display-name API")
    require_false(display_api, "mutates_ids", "client-build-manifest.json")
    require_true(display_api, "protocol_safe", "client-build-manifest.json")

    rendered = read_json(paths["protocol-render-invariants.json"])
    if rendered.get("task") != "Phase 1 T1-10":
        raise AssertionError("Rendered protocol fixture is not the T1-10 report")
    require_true(rendered, "raw_protocol_unchanged", "protocol-render-invariants.json")
    require_true(rendered, "choose_command_unchanged", "protocol-render-invariants.json")

    engine = read_json(paths["poke-engine-boundary-report.json"])
    if engine.get("task") != "Phase 1 T1-12":
        raise AssertionError("Rust boundary report is not the T1-12 report")
    require_true(engine, "verified", "poke-engine-boundary-report.json")
    require_true(engine, "state_round_trip_exact", "poke-engine-boundary-report.json")
    require_false(
        engine,
        "rust_boundary_contains_japanese_names",
        "poke-engine-boundary-report.json",
    )
    expected_ids = {
        "species": "pikachu",
        "move": "thunderbolt",
        "ability": "static",
        "item": "lightball",
    }
    if engine.get("target_ids") != expected_ids:
        raise AssertionError("Rust boundary report changed the normalized target IDs")

    foul_play = task_report_from_log(
        paths["bss-foul-play-input-invariants.log"], "Phase 1 T1-11"
    )
    require_true(foul_play, "verified", "bss-foul-play-input-invariants.log")
    require_false(
        foul_play,
        "bot_received_japanese_names",
        "bss-foul-play-input-invariants.log",
    )

    server_protocol = task_report_from_log(
        paths["bss-protocol-invariants.log"], "Phase 1 T1-10"
    )
    require_true(server_protocol, "verified", "bss-protocol-invariants.log")
    require_false(
        server_protocol,
        "raw_protocol_contains_japanese_display_names",
        "bss-protocol-invariants.log",
    )

    require_text(
        paths["authenticated-launcher.html"],
        ("National Dex All Generations BSS", "名前を保存してShowdownを開く"),
    )
    require_text(
        paths["authenticated-client.headers"],
        ("x-pokemon-showdown-client-source: pinned-local",),
        ignore_case=True,
    )
    require_text(
        paths["authenticated-client.html"],
        (
            "Config.defaultserver",
            "prefix: '/showdown'",
            "language: 'japanese'",
            'src="/config/config.js"',
        ),
    )
    require_text(
        paths["client-main.headers"],
        (
            "x-pokemon-showdown-client-source: pinned-local",
            "cache-control: public, max-age=31536000, immutable",
        ),
        ignore_case=True,
    )
    require_text(
        paths["client-config.headers"],
        ("x-pokemon-showdown-client-source: pinned-local",),
        ignore_case=True,
    )
    require_text(paths["client-config.js"], ("Config.version",))
    require_text(
        paths["local-client-alias.headers"],
        ("x-pokemon-showdown-client-source: pinned-local",),
        ignore_case=True,
    )
    require_text(paths["unknown-path.txt"], ("Not found.",))

    screenshots: dict[str, dict[str, Any]] = {}
    for filename in ("phase1-launcher-ipad.png", "phase1-client-ipad.png"):
        dimensions = png_size(paths[filename])
        if dimensions != EXPECTED_SCREENSHOT_SIZE:
            raise AssertionError(
                f"{filename} has size {dimensions}; expected {EXPECTED_SCREENSHOT_SIZE}"
            )
        screenshots[filename] = {
            "width": dimensions[0],
            "height": dimensions[1],
            "bytes": paths[filename].stat().st_size,
            "sha256": sha256(paths[filename]),
        }

    artifact_manifest = {
        name: {"bytes": path.stat().st_size, "sha256": sha256(path)}
        for name, path in sorted(paths.items())
    }
    criteria = {
        "clean_docker_build": statuses["docker_clean_build"] == 0,
        "all_regression_tests_passed": all(value == 0 for value in statuses.values()),
        "pinned_client_verified": client_pin["remote_verified"] is True,
        "browser_delivery_verified": True,
        "ipad_visual_artifacts_verified": True,
        "artifact_manifest_complete": len(artifact_manifest) == len(REQUIRED_ARTIFACTS),
        "protected_boundaries_unchanged": baseline["protected_paths_changed"] == [],
    }
    if not all(criteria.values()):
        raise AssertionError(f"Phase 1 integration criteria are incomplete: {criteria}")

    return {
        "phase": "Phase 1",
        "task": "T1-13",
        "title": "Phase 1 integration regression",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "commit": os.environ.get(
            "PHASE1_TARGET_SHA",
            os.environ.get("GITHUB_SHA", baseline.get("commit", "unknown")),
        ),
        "workflow_run_id": os.environ.get("PHASE1_RENDER_RUN_ID", ""),
        "pinned_client_commit": EXPECTED_CLIENT_COMMIT,
        "completion_criteria": criteria,
        "status_files": statuses,
        "verified_reports": {
            "t1_10_rendered_protocol": True,
            "t1_10_live_server_protocol": True,
            "t1_11_foul_play_input": True,
            "t1_12_rust_boundary": True,
            "bss_turn_one": True,
            "post_faint_recovery": True,
        },
        "browser_verification": {
            "access_gate": True,
            "pinned_local_client": True,
            "same_origin_showdown": True,
            "japanese_language_bootstrap": True,
            "screenshots": screenshots,
        },
        "artifact_audit": {
            "artifact_count": len(artifact_manifest),
            "files": artifact_manifest,
        },
        "phase1_complete": True,
        "ready_for_phase2": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit Phase 1 integration evidence and produce the T1-13 release report."
    )
    parser.add_argument("--artifact-root", type=pathlib.Path, default=pathlib.Path("/tmp"))
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()

    report = build_report(args.artifact_root.resolve())
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")


if __name__ == "__main__":
    main()
