#!/usr/bin/env python3
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

REQUIRED_WORKFLOWS = (
    "Localization documentation",
    "Node.js CI",
    "Render smoke test",
    "Phase 1 integration regression",
    "Phase 3 baseline inventory",
)

def github_json(repository: str, sha: str, token: str) -> dict[str, Any]:
    query = urllib.parse.urlencode({"head_sha": sha, "per_page": 100})
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/actions/runs?{query}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "pokemon-showdown-phase3-integration-gate",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub Actions API {error.code}: {detail}") from error
    if not isinstance(payload, dict):
        raise RuntimeError("GitHub Actions API returned a non-object payload")
    return payload

def compact(run: dict[str, Any]) -> dict[str, Any]:
    return {key: run.get(key) for key in (
        "id", "name", "event", "status", "conclusion", "head_sha", "run_number",
        "run_attempt", "html_url", "created_at", "updated_at",
    )}

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--timeout", type=float, default=5400)
    parser.add_argument("--interval", type=float, default=15)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required")
    deadline = time.monotonic() + args.timeout
    previous: dict[str, Any] = {}
    while time.monotonic() < deadline:
        runs = github_json(args.repository, args.sha, token).get("workflow_runs", [])
        selected: dict[str, dict[str, Any]] = {}
        for run in runs:
            name = run.get("name")
            if name not in REQUIRED_WORKFLOWS:
                continue
            if name not in selected or int(run.get("id", 0)) > int(selected[name].get("id", 0)):
                selected[name] = run
        snapshot = {name: compact(selected[name]) for name in selected}
        if snapshot != previous:
            print(json.dumps(snapshot, indent=2, sort_keys=True))
            previous = snapshot
        missing = [name for name in REQUIRED_WORKFLOWS if name not in selected]
        if missing:
            time.sleep(args.interval)
            continue
        failures = {name: run.get("conclusion") for name, run in selected.items()
                    if run.get("status") == "completed" and run.get("conclusion") != "success"}
        if failures:
            raise SystemExit(f"Phase 3 prerequisite workflow failure: {failures}")
        if any(run.get("status") != "completed" for run in selected.values()):
            time.sleep(args.interval)
            continue
        result = {
            "phase": "Phase 3",
            "task": "T3-08",
            "repository": args.repository,
            "target_sha": args.sha,
            "checked_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
            "required_workflows": {name: compact(selected[name]) for name in REQUIRED_WORKFLOWS},
            "all_required_workflows_successful": True,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2, sort_keys=True))
        return
    raise TimeoutError(f"Timed out waiting for Phase 3 prerequisites: {previous}")

if __name__ == "__main__":
    main()
