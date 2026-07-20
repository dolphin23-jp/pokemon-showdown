#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/.runtime"
BSS_DIR="$RUNTIME_DIR/bss-teams/gen9bssregi-curated"
TARGET_DIR="$RUNTIME_DIR/bss-teams/gen9nationaldexallgenerationsbss"
METADATA_FILE="$RUNTIME_DIR/bss-teams/gen9nationaldexallgenerationsbss.tsv"
FORMAT="gen9nationaldexallgenerationsbss"
LIMIT="${ALL_GENERATIONS_TEAM_LIMIT:-48}"
REFRESH=0

if [[ "${1:-}" == "--refresh" ]]; then
    REFRESH=1
elif [[ -n "${1:-}" ]]; then
    echo "Usage: bash scripts/sync-all-generations-teams.sh [--refresh]" >&2
    exit 2
fi

existing_count=0
if [[ -d "$TARGET_DIR" ]]; then
    existing_count="$(find "$TARGET_DIR" -maxdepth 1 -type f -name '*.txt' | wc -l | tr -d ' ')"
fi
if [[ "$REFRESH" -eq 0 && "$existing_count" -ge 12 && -f "$METADATA_FILE" ]]; then
    echo "All-generations team library is ready ($existing_count teams)."
    exit 0
fi

# The curated Regulation I teams are reliable fallback seeds if the community API
# is unavailable during an image build or a cold start.
bash "$ROOT_DIR/scripts/sync-bss-teams.sh"

mkdir -p "$RUNTIME_DIR/bss-teams"
TEMP_DIR="$(mktemp -d "$RUNTIME_DIR/bss-teams/.all-generations.XXXXXX")"
TEMP_METADATA="$TEMP_DIR/metadata.tsv"
trap 'rm -rf "$TEMP_DIR"' EXIT

python3 - "$ROOT_DIR" "$BSS_DIR" "$TEMP_DIR" "$TEMP_METADATA" "$FORMAT" "$LIMIT" <<'PY'
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request

root = pathlib.Path(sys.argv[1])
seed_dir = pathlib.Path(sys.argv[2])
out_dir = pathlib.Path(sys.argv[3])
metadata_path = pathlib.Path(sys.argv[4])
format_id = sys.argv[5]
limit = max(12, int(sys.argv[6]))
showdown = root / "pokemon-showdown"
manifest = root / "config" / "bss-team-sources.tsv"

records: list[tuple[str, str, str, str, str]] = []
seen: set[str] = set()

def slugify(value: str, fallback: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return (value[:64] or fallback)


def run_showdown(command: str, text: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["node", str(showdown), command, format_id] if command == "validate-team" else ["node", str(showdown), command],
        input=text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=root,
        timeout=90,
    )


def normalize_export(team_text: str) -> str | None:
    exported = run_showdown("export-team", team_text)
    if exported.returncode != 0:
        return None
    text = exported.stdout.strip()
    if not text:
        return None
    # foul-play currently does not support Z-Moves or Dynamax. Keep the library
    # broad, but exclude teams that depend on those unsupported mechanics.
    if re.search(r"@\s+.*ium Z(?:\s|$)", text, re.IGNORECASE):
        return None
    if "Dynamax Level:" in text or "Gigantamax: Yes" in text:
        return None
    members = [block for block in re.split(r"\n\s*\n", text) if block.strip()]
    if len(members) != 6:
        return None
    validated = run_showdown("validate-team", text)
    if validated.returncode != 0:
        return None
    return text + "\n"


def add_team(team_id: str, title: str, author: str, packed_or_exported: str, source: str) -> bool:
    normalized = normalize_export(packed_or_exported)
    if normalized is None:
        return False
    digest = hashlib.sha256(normalized.encode()).hexdigest()
    if digest in seen:
        return False
    seen.add(digest)
    slug = slugify(title, f"team-{team_id}")
    candidate = slug
    suffix = 2
    while (out_dir / f"{candidate}.txt").exists():
        candidate = f"{slug}-{suffix}"
        suffix += 1
    (out_dir / f"{candidate}.txt").write_text(normalized, encoding="utf-8")
    records.append((team_id, candidate, title, author, source))
    return True


# Seed the broad format with all known-good curated BSS teams.
seed_meta: dict[str, tuple[str, str, str]] = {}
if manifest.exists():
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        team_id, slug, title, author, *_ = line.split("\t")
        seed_meta[slug] = (team_id, title, author)
if seed_dir.exists():
    for team_file in sorted(seed_dir.glob("*.txt")):
        team_id, title, author = seed_meta.get(team_file.stem, (f"seed-{team_file.stem}", team_file.stem, "BSS Sample Teams"))
        add_team(team_id, title, author, team_file.read_text(encoding="utf-8"), "curated-bss")


def fetch_json(url: str) -> object:
    request = urllib.request.Request(url, headers={"User-Agent": "Pokemon-Showdown-AI-Team-Sync/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read().decode("utf-8").strip()
    if raw.startswith("]"):
        raw = raw[1:]
    return json.loads(raw)


def rows_from_payload(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("result", "teams", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
    return []


# Community National Dex formats provide much more variety than the nine curated
# Regulation I teams. Search several compatible pools and keep only teams that
# still validate in our embedded all-generations format.
search_formats = [
    "gen9nationaldexag",
    "gen9nationaldexubers",
    "gen9nationaldex",
]
for source_format in search_formats:
    if len(records) >= limit:
        break
    url = "https://teams.pokemonshowdown.com/api/searchteams?" + urllib.parse.urlencode({
        "format": source_format,
        "count": min(200, limit * 4),
    })
    try:
        rows = rows_from_payload(fetch_json(url))
    except Exception as error:
        print(f"Warning: could not search {source_format}: {error}", file=sys.stderr)
        continue
    for row in rows:
        if len(records) >= limit:
            break
        team_id = str(row.get("teamid") or row.get("id") or "community")
        title = str(row.get("name") or row.get("title") or f"Community team {team_id}")
        author = str(row.get("ownerid") or row.get("owner") or "Pokemon Showdown community")
        team = row.get("team")
        if not isinstance(team, str) or not team:
            try:
                detail = fetch_json(
                    "https://teams.pokemonshowdown.com/api/getteam?" +
                    urllib.parse.urlencode({"teamid": team_id, "full": 1})
                )
                if isinstance(detail, dict):
                    team = detail.get("team")
                    title = str(detail.get("name") or detail.get("title") or title)
                    author = str(detail.get("ownerid") or detail.get("owner") or author)
            except Exception:
                team = None
        if isinstance(team, str) and team:
            add_team(team_id, title, author, team, source_format)

if len(records) < 3:
    raise SystemExit(f"Only {len(records)} compatible teams were prepared; at least 3 are required.")

metadata_path.write_text(
    "# team_id\tslug\ttitle\tauthor\tsource\n" +
    "".join("\t".join(record) + "\n" for record in records),
    encoding="utf-8",
)
print(f"Prepared {len(records)} compatible all-generations teams.")
PY

# Move the metadata outside the team directory; foul-play treats every regular
# file inside the selected directory as a possible team.
mv "$TEMP_METADATA" "$RUNTIME_DIR/bss-teams/.all-generations-metadata.tsv"
rm -rf "$TARGET_DIR"
mv "$TEMP_DIR" "$TARGET_DIR"
mv "$RUNTIME_DIR/bss-teams/.all-generations-metadata.tsv" "$METADATA_FILE"
trap - EXIT

team_count="$(find "$TARGET_DIR" -maxdepth 1 -type f -name '*.txt' | wc -l | tr -d ' ')"
echo "All-generations team library updated: $team_count teams ready."
