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
)


def github_json(repository: str, sha: str, token: str) -> dict[str, Any]:
    query = urllib.parse.urlencode({"head_sha": sha, "per_page": 100})
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/actions/runs?{query}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "pokemon-showdown-phase1-integration-gate",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"GitHub Actions API {error.code} for {repository}@{sha}: {detail}"
        ) from error
    if not isinstance(payload, dict):
        raise RuntimeError("GitHub Actions API returned a non-object payload")
    return payload


def latest_required_runs(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    runs = payload.get("workflow_runs")
    if not isinstance(runs, list):
        raise RuntimeError("GitHub Actions API response is missing workflow_runs")

    selected: dict[str, dict[str, Any]] = {}
    for run in runs:
        if not isinstance(run, dict):
            continue
        name = run.get("name")
        if name not in REQUIRED_WORKFLOWS:
            continue
        current = selected.get(name)
        if current is None or int(run.get("id", 0)) > int(current.get("id", 0)):
            selected[name] = run
    return selected


def compact_run(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": run.get("id"),
        "name": run.get("name"),
        "event": run.get("event"),
        "status": run.get("status"),
        "conclusion": run.get("conclusion"),
        "head_sha": run.get("head_sha"),
        "run_number": run.get("run_number"),
        "run_attempt": run.get("run_attempt"),
        "html_url": run.get("html_url"),
        "created_at": run.get("created_at"),
        "updated_at": run.get("updated_at"),
    }


def append_github_output(path: pathlib.Path, values: dict[str, str]) -> None:
    with path.open("a", encoding="utf-8") as stream:
        for key, value in values.items():
            stream.write(f"{key}={value}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Wait for the three Phase 1 prerequisite workflows on one commit."
    )
    parser.add_argument("--repository", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--timeout", type=float, default=4200)
    parser.add_argument("--interval", type=float, default=15)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--github-output", type=pathlib.Path)
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required to inspect workflow runs")

    deadline = time.monotonic() + args.timeout
    last_snapshot: dict[str, dict[str, Any]] = {}
    while time.monotonic() < deadline:
        payload = github_json(args.repository, args.sha, token)
        selected = latest_required_runs(payload)
        snapshot = {name: compact_run(run) for name, run in selected.items()}
        if snapshot != last_snapshot:
            print(json.dumps(snapshot, indent=2, sort_keys=True))
            last_snapshot = snapshot

        missing = [name for name in REQUIRED_WORKFLOWS if name not in selected]
        if missing:
            time.sleep(args.interval)
            continue

        failures = {
            name: run.get("conclusion")
            for name, run in selected.items()
            if run.get("status") == "completed" and run.get("conclusion") != "success"
        }
        if failures:
            raise SystemExit(f"Phase 1 prerequisite workflow failure: {failures}")

        incomplete = [
            name
            for name, run in selected.items()
            if run.get("status") != "completed"
        ]
        if incomplete:
            time.sleep(args.interval)
            continue

        render_run = selected["Render smoke test"]
        result = {
            "task": "Phase 1 T1-13",
            "repository": args.repository,
            "target_sha": args.sha,
            "checked_at": dt.datetime.now(dt.timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "required_workflows": {
                name: compact_run(selected[name]) for name in REQUIRED_WORKFLOWS
            },
            "all_required_workflows_successful": True,
            "render_smoke_run_id": int(render_run["id"]),
        }
        payload_text = json.dumps(result, indent=2, sort_keys=True) + "\n"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload_text, encoding="utf-8")
        print(payload_text, end="")

        if args.github_output:
            append_github_output(
                args.github_output,
                {
                    "render_smoke_run_id": str(render_run["id"]),
                    "target_sha": args.sha,
                },
            )
        return

    raise TimeoutError(
        "Timed out waiting for Localization documentation, Node.js CI, and Render smoke test "
        f"for {args.repository}@{args.sha}. Last snapshot: {last_snapshot}"
    )


if __name__ == "__main__":
    main()
