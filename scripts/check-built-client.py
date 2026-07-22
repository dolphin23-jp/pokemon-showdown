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

DISPLAY_NAME_FUNCTIONS = (
    "displaySpeciesName",
    "displayMoveName",
    "displayAbilityName",
    "displayItemName",
)

DISPLAY_NAME_SOURCE_REPOSITORY = "PokeAPI/pokeapi"
DISPLAY_NAME_SOURCE_COMMIT = "227b573712414a86ba299d322fa398fbb2893edc"
DISPLAY_NAME_LANGUAGE_ID = 11
DISPLAY_NAME_MINIMUM_COUNTS = {
    "species": 1000,
    "moves": 800,
    "abilities": 250,
    "items": 1500,
}

BATTLE_CONTROL_SELECTORS = (
    "button.movebutton",
    'button[data-tooltip^="switchpokemon|"]',
    'button[data-tooltip^="allypokemon|"]',
    'button[data-tooltip^="activepokemon|"]',
)

BATTLE_LOG_CATEGORIES = (
    "battle flow",
    "moves",
    "switching",
    "fainting",
    "effectiveness",
    "critical hits",
    "status conditions",
    "weather",
    "terrain",
    "stat changes",
    "damage and healing",
    "items and abilities",
)

REQUIRED_ARTIFACTS = (
    "config/config.js",
    "config/japanese-display-name-api.json",
    "play.pokemonshowdown.com/testclient-new.html",
    "play.pokemonshowdown.com/index-new.html",
    "play.pokemonshowdown.com/battle-text-ja-smoke.html",
    "play.pokemonshowdown.com/src/battle-display-names.ts",
    "play.pokemonshowdown.com/src/battle-text-ja.js",
    "play.pokemonshowdown.com/src/battle-text-ja-smoke.js",
    "play.pokemonshowdown.com/js/battle-display-names.js",
    "play.pokemonshowdown.com/js/battle-display-names.meta.json",
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


def validate_display_name_api(client_root: pathlib.Path, testclient: str) -> dict[str, Any]:
    contract_path = client_root / "config" / "japanese-display-name-api.json"
    source_path = (
        client_root / "play.pokemonshowdown.com" / "src" / "battle-display-names.ts"
    )
    compiled_path = (
        client_root / "play.pokemonshowdown.com" / "js" / "battle-display-names.js"
    )
    metadata_path = (
        client_root
        / "play.pokemonshowdown.com"
        / "js"
        / "battle-display-names.meta.json"
    )
    battle_log_path = (
        client_root / "play.pokemonshowdown.com" / "src" / "battle-text-ja.js"
    )
    battle_log_smoke_path = (
        client_root / "play.pokemonshowdown.com" / "src" / "battle-text-ja-smoke.js"
    )
    battle_log_page_path = (
        client_root / "play.pokemonshowdown.com" / "battle-text-ja-smoke.html"
    )
    index_path = client_root / "play.pokemonshowdown.com" / "index-new.html"

    contract = read_json(contract_path)
    expected_contract = {
        "api_global": "PSDisplayNames",
        "data_global": "BattleJapaneseDisplayNames",
        "functions": list(DISPLAY_NAME_FUNCTIONS),
        "fallback": "canonical-english-name",
        "generated_data": {
            "generator": "build-tools/generate-japanese-display-names.js",
            "command": "npm run generate-japanese-display-names",
            "source_repository": DISPLAY_NAME_SOURCE_REPOSITORY,
            "source_commit": DISPLAY_NAME_SOURCE_COMMIT,
            "language_id": DISPLAY_NAME_LANGUAGE_ID,
            "compiled_output": "play.pokemonshowdown.com/js/battle-display-names.js",
            "metadata_output": "play.pokemonshowdown.com/js/battle-display-names.meta.json",
            "minimum_counts": DISPLAY_NAME_MINIMUM_COUNTS,
        },
        "battle_controls": {
            "task": "T1-09",
            "translated_categories": ["moves", "species"],
            "selectors": list(BATTLE_CONTROL_SELECTORS),
            "display_text_only": True,
            "mutates_commands": False,
            "mutates_tooltips": False,
            "preserves_unknown_names": True,
        },
        "battle_log": {
            "template_source": "play.pokemonshowdown.com/src/battle-text-ja.js",
            "translated_categories": list(BATTLE_LOG_CATEGORIES),
            "display_name_api": "PSDisplayNames",
            "display_text_only": True,
            "mutates_protocol_args": False,
            "preserves_number_placeholders": True,
        },
        "mutates_ids": False,
        "protocol_safe": True,
    }
    if contract != expected_contract:
        raise AssertionError("Japanese display-name API contract is missing or unexpected")

    source = source_path.read_text(encoding="utf-8")
    source_markers = (
        "localizeBattleControlButton",
        "localizeBattleControls",
        "MutationObserver",
        "characterData: true",
        "textNode.nodeValue = rawName.replace(name, translatedName)",
        *BATTLE_CONTROL_SELECTORS,
    )
    missing_source_markers = [marker for marker in source_markers if marker not in source]
    if missing_source_markers:
        raise AssertionError(
            f"Battle-control localization source is missing markers: {missing_source_markers}"
        )
    forbidden_source_markers = (
        "setAttribute('data-cmd'",
        'setAttribute("data-cmd"',
        "setAttribute('data-tooltip'",
        'setAttribute("data-tooltip"',
        ".dataset.cmd =",
        ".dataset.tooltip =",
    )
    present_forbidden_markers = [
        marker for marker in forbidden_source_markers if marker in source
    ]
    if present_forbidden_markers:
        raise AssertionError(
            "Battle-control localization must not mutate command or tooltip attributes: "
            + ", ".join(present_forbidden_markers)
        )

    battle_log_source = battle_log_path.read_text(encoding="utf-8")
    battle_log_markers = (
        "JAPANESE_BATTLE_TEXT",
        "superEffective",
        "crit",
        "brn",
        "raindance",
        "localizeRenderedNames",
        "originalParseArgsInner",
        "PSDisplayNames",
        "[NUMBER]",
        "[PERCENTAGE]",
        "japaneseBattleTextInstalled",
    )
    missing_battle_log_markers = [
        marker for marker in battle_log_markers if marker not in battle_log_source
    ]
    if missing_battle_log_markers:
        raise AssertionError(
            f"Japanese battle-log source is missing markers: {missing_battle_log_markers}"
        )
    if "args[" not in battle_log_source or "kwArgs" not in battle_log_source:
        raise AssertionError("Japanese battle-log source does not read parser display inputs")

    index = index_path.read_text(encoding="utf-8")
    text_position = index.find('src="/data/text.js?"')
    japanese_position = index.find('src="/src/battle-text-ja.js?"')
    battle_position = index.find('src="/js/battle.js?"')
    if not (0 <= text_position < japanese_position < battle_position):
        raise AssertionError(
            "Japanese battle-log templates must load after text.js and before battle.js"
        )

    battle_log_page = battle_log_page_path.read_text(encoding="utf-8")
    battle_log_smoke = battle_log_smoke_path.read_text(encoding="utf-8")
    for marker in (
        "battle-text-ja.js",
        "battle-text-ja-smoke.js",
        "battle-log",
    ):
        if marker not in battle_log_page:
            raise AssertionError(f"Battle-log smoke page is missing marker: {marker}")
    for marker in (
        "battle-log-smoke.txt",
        "battle-log-smoke.json",
        "BattleTextParser",
        "効果はばつぐんだ！",
        "急所に当たった！",
        "まひして技が出にくくなった！",
        "dataset.verified",
    ):
        if marker not in battle_log_smoke:
            raise AssertionError(f"Battle-log smoke renderer is missing marker: {marker}")

    compiled = compiled_path.read_text(encoding="utf-8")
    missing_markers = [
        marker
        for marker in (
            "PSDisplayNames",
            "BattleJapaneseDisplayNames",
            "BEGIN GENERATED JAPANESE DISPLAY NAMES",
            "END GENERATED JAPANESE DISPLAY NAMES",
            DISPLAY_NAME_SOURCE_COMMIT,
            "localizeBattleControlButton",
            "MutationObserver",
            *DISPLAY_NAME_FUNCTIONS,
            *BATTLE_CONTROL_SELECTORS,
        )
        if marker not in compiled
    ]
    if missing_markers:
        raise AssertionError(
            f"Compiled display-name API is missing markers: {missing_markers}"
        )
    if 'src="js/battle-display-names.js"' not in testclient:
        raise AssertionError("Pinned test client does not load the display-name API")

    metadata = read_json(metadata_path)
    if metadata.get("source_repository") != DISPLAY_NAME_SOURCE_REPOSITORY:
        raise AssertionError("Generated display-name source repository is unexpected")
    if metadata.get("source_commit") != DISPLAY_NAME_SOURCE_COMMIT:
        raise AssertionError("Generated display-name source commit is unexpected")
    if metadata.get("language_id") != DISPLAY_NAME_LANGUAGE_ID:
        raise AssertionError("Generated display-name language is unexpected")
    if metadata.get("output") != "play.pokemonshowdown.com/js/battle-display-names.js":
        raise AssertionError("Generated display-name output path is unexpected")
    if metadata.get("generated_data_only") is not True:
        raise AssertionError("Generated display-name metadata must remain display-only")
    if metadata.get("mutates_ids") is not False:
        raise AssertionError("Generated display-name metadata must not mutate IDs")
    if metadata.get("protocol_safe") is not True:
        raise AssertionError("Generated display-name metadata must remain protocol-safe")

    counts = metadata.get("counts")
    if not isinstance(counts, dict):
        raise AssertionError("Generated display-name metadata is missing counts")
    for table, minimum in DISPLAY_NAME_MINIMUM_COUNTS.items():
        count = counts.get(table)
        if not isinstance(count, int) or count < minimum:
            raise AssertionError(
                f"Generated display-name table {table} has {count}; expected at least {minimum}"
            )

    return {
        "contract": str(contract_path.relative_to(client_root)),
        "source": str(source_path.relative_to(client_root)),
        "compiled_api": str(compiled_path.relative_to(client_root)),
        "generated_metadata": str(metadata_path.relative_to(client_root)),
        "api_global": contract["api_global"],
        "data_global": contract["data_global"],
        "functions": contract["functions"],
        "fallback": contract["fallback"],
        "source_repository": metadata["source_repository"],
        "source_commit": metadata["source_commit"],
        "language_id": metadata["language_id"],
        "counts": counts,
        "battle_controls": contract["battle_controls"],
        "battle_log": contract["battle_log"],
        "mutates_ids": contract["mutates_ids"],
        "protocol_safe": contract["protocol_safe"],
        "generated_map_present": True,
    }


def validate_build(client_root: pathlib.Path, pin_file: pathlib.Path) -> dict[str, Any]:
    pin = read_json(pin_file)
    missing = [
        relative
        for relative in ("package.json", *REQUIRED_ARTIFACTS)
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

    testclient = (
        client_root / "play.pokemonshowdown.com" / "testclient-new.html"
    ).read_text(encoding="utf-8")
    required_references = (
        'href="style/client2.css"',
        'src="js/battle-display-names.js"',
        'src="js/client-main.js"',
        'src="js/client-connection.js"',
        'src="js/panel-battle.js"',
    )
    missing_references = [
        reference for reference in required_references if reference not in testclient
    ]
    if missing_references:
        raise AssertionError(
            f"Local test client is missing required build references: {missing_references}"
        )

    manifest = expected_manifest(client_root, pin)
    manifest["display_name_api"] = validate_display_name_api(client_root, testclient)
    return manifest


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
        "display_name_api": manifest["display_name_api"],
        "verified": True,
    }
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")


if __name__ == "__main__":
    main()
