#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_PIN_FILE = ROOT / "config" / "pokemon-showdown-client.json"

REQUIRED_ARTIFACTS = (
    "config/config.js",
    "play.pokemonshowdown.com/caches/index-new.html",
    "play.pokemonshowdown.com/js/client-main.js",
    "play.pokemonshowdown.com/js/client-connection.js",
    "play.pokemonshowdown.com/js/panel-battle.js",
    "play.pokemonshowdown.com/style/client2.css",
)


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def git_head(client_root: pathlib.Path) -> str | None:
    if not (client_root / ".git").exists():
        return None
    result = subprocess.run(
        ["git", "-C", str(client_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def expected_manifest(client_root: pathlib.Path, pin: dict[str, Any]) -> dict[str, Any]:
    package = read_json(client_root / "package.json")
    artifacts = {
        relative: {
            "bytes": (client_root / relative).stat().st_size,
            "sha256": sha256(client_root / relative),
        }
        for relative in REQUIRED_ARTIFACTS
    }
    return {
        "repository": pin["fork_repository"],
        "upstream_repository": pin["upstream_repository"],
        "commit": pin["commit"],
        "client_version": package["version"],
        "build_command": "npm ci && npm run build",
        "artifacts": artifacts,
    }


def validate_build(client_root: pathlib.Path, pin_file: pathlib.Path) -> dict[str, Any]:
    pin = read_json(pin_file)
    missing = [
        relative for relative in ("package.json", *REQUIRED_ARTIFACTS)
        if not (client_root / relative).is_file()
    ]
    if missing:
        raise AssertionError(f"Missing pinned client build artifacts: {missing}")

    head = git_head(client_root)
    if head is not None and head != pin["commit"]:
        raise AssertionError(f"Client source HEAD mismatch: expected {pin['commit']}, found {head}")

    short_sha = pin["commit"][:8]
    config = (client_root / "config" / "config.js").read_text(encoding="utf-8")
    if not re.search(rf'Config\.version = "[^"]*\({short_sha}\)";', config):
        raise AssertionError("Built client config does not contain the pinned commit version")

    index = (
        client_root / "play.pokemonshowdown.com" / "caches" / "index-new.html"
    ).read_text(encoding="utf-8")
    required_cachebusters = (
        r'/style/client2\.css\?[0-9a-f]{8}',
        r'/js/client-main\.js\?[0-9a-f]{8}',
        r'/js/client-connection\.js\?[0-9a-f]{8}',
    )
    missing_cachebusters = [
        pattern for pattern in required_cachebusters
        if not re.search(pattern, index)
    ]
    if missing_cachebusters:
        raise AssertionError(
            f"Built client index is missing cache-busted assets: {missing_cachebusters}"
        )
    if "<!-- newsid -->" in index or "<!-- build-tools/news-embed.php -->" in index:
        raise AssertionError("Built client index still contains unresolved build placeholders")

    return expected_manifest(client_root, pin)


def verify_manifest(manifest_path: pathlib.Path, expected: dict[str, Any]) -> None:
    if not manifest_path.is_file():
        raise AssertionError(f"Missing build manifest: {manifest_path}")
    actual = read_json(manifest_path)
    if actual != expected:
        raise AssertionError("Pinned client build manifest does not match the embedded artifacts")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the pinned client build artifacts.")
    parser.add_argument("--client-root", type=pathlib.Path, required=True)
    parser.add_argument("--pin-file", type=pathlib.Path, default=DEFAULT_PIN_FILE)
    parser.add_argument("--manifest", type=pathlib.Path)
    parser.add_argument("--write-manifest", action="store_true")
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()

    client_root = args.client_root.resolve()
    pin_file = args.pin_file.resolve()
    manifest_path = (args.manifest or client_root / "build-manifest.json").resolve()
    manifest = validate_build(client_root, pin_file)

    if args.write_manifest:
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    else:
        verify_manifest(manifest_path, manifest)

    report = {
        "client_root": str(client_root),
        "manifest": str(manifest_path),
        "repository": manifest["repository"],
        "commit": manifest["commit"],
        "client_version": manifest["client_version"],
        "artifact_count": len(manifest["artifacts"]),
        "verified": True,
    }
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")


if __name__ == "__main__":
    main()
