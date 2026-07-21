#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import urllib.error
import urllib.request
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
PIN_FILE = ROOT / "config" / "pokemon-showdown-client.json"
EXPECTED_FORK = "dolphin23-jp/pokemon-showdown-client"
EXPECTED_UPSTREAM = "smogon/pokemon-showdown-client"
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def load_pin() -> dict[str, Any]:
    payload = json.loads(PIN_FILE.read_text(encoding="utf-8"))
    required = {
        "fork_repository",
        "upstream_repository",
        "commit",
        "upstream_commit_date",
        "runtime_delivery_changed",
    }
    missing = sorted(required - payload.keys())
    extra = sorted(payload.keys() - required)
    if missing or extra:
        raise AssertionError(f"Unexpected client pin fields; missing={missing}, extra={extra}")
    if payload["fork_repository"] != EXPECTED_FORK:
        raise AssertionError(f"Unexpected client fork: {payload['fork_repository']}")
    if payload["upstream_repository"] != EXPECTED_UPSTREAM:
        raise AssertionError(f"Unexpected client upstream: {payload['upstream_repository']}")
    if not SHA_PATTERN.fullmatch(str(payload["commit"])):
        raise AssertionError("Pinned client commit must be a full lowercase 40-character SHA")
    if not isinstance(payload["runtime_delivery_changed"], bool):
        raise AssertionError("runtime_delivery_changed must be a JSON boolean")
    return payload


def github_json(path: str) -> dict[str, Any]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "pokemon-showdown-ai-client-pin-check",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"https://api.github.com{path}", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API {error.code} for {path}: {detail}") from error


def verify_remote(pin: dict[str, Any]) -> dict[str, Any]:
    fork = github_json(f"/repos/{pin['fork_repository']}")
    if fork.get("fork") is not True:
        raise AssertionError(f"{pin['fork_repository']} is not reported as a GitHub fork")
    parent = (fork.get("parent") or {}).get("full_name")
    if parent != pin["upstream_repository"]:
        raise AssertionError(
            f"Fork parent mismatch: expected {pin['upstream_repository']}, found {parent}"
        )

    commit = github_json(
        f"/repos/{pin['fork_repository']}/commits/{pin['commit']}"
    )
    if commit.get("sha") != pin["commit"]:
        raise AssertionError("Pinned client commit was not resolved exactly in the fork")

    upstream_commit = github_json(
        f"/repos/{pin['upstream_repository']}/commits/{pin['commit']}"
    )
    if upstream_commit.get("sha") != pin["commit"]:
        raise AssertionError("Pinned client commit was not resolved exactly upstream")

    return {
        "fork": fork.get("full_name"),
        "parent": parent,
        "commit": commit.get("sha"),
        "default_branch": fork.get("default_branch"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the pinned Pokemon Showdown client fork.")
    parser.add_argument("--verify-remote", action="store_true")
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()

    pin = load_pin()
    report: dict[str, Any] = {
        "pin_file": str(PIN_FILE.relative_to(ROOT)),
        "fork_repository": pin["fork_repository"],
        "upstream_repository": pin["upstream_repository"],
        "commit": pin["commit"],
        "runtime_delivery_changed": pin["runtime_delivery_changed"],
        "remote_verified": False,
    }
    if args.verify_remote:
        report["remote"] = verify_remote(pin)
        report["remote_verified"] = True

    output = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    print(output, end="")


if __name__ == "__main__":
    main()
