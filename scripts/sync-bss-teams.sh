#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="$ROOT_DIR/config/bss-team-sources.tsv"
TEAM_PARENT="$ROOT_DIR/.runtime/bss-teams"
TARGET_DIR="$TEAM_PARENT/gen9bssregi-curated"
REFRESH=0

if [[ "${1:-}" == "--refresh" ]]; then
    REFRESH=1
elif [[ -n "${1:-}" ]]; then
    echo "Usage: bash scripts/sync-bss-teams.sh [--refresh]" >&2
    exit 2
fi

if [[ ! -f "$MANIFEST" ]]; then
    echo "BSS team manifest is missing: $MANIFEST" >&2
    exit 1
fi

expected_count="$(grep -Ev '^[[:space:]]*(#|$)' "$MANIFEST" | wc -l | tr -d ' ')"
existing_count=0
if [[ -d "$TARGET_DIR" ]]; then
    existing_count="$(find "$TARGET_DIR" -maxdepth 1 -type f -name '*.txt' | wc -l | tr -d ' ')"
fi

if [[ "$REFRESH" -eq 0 && "$existing_count" -ge "$expected_count" && "$expected_count" -gt 0 ]]; then
    echo "BSS team library is ready ($existing_count teams)."
    exit 0
fi

mkdir -p "$TEAM_PARENT" "$ROOT_DIR/.runtime"
TEMP_DIR="$(mktemp -d "$TEAM_PARENT/.gen9bssregi-curated.XXXXXX")"
trap 'rm -rf "$TEMP_DIR"' EXIT

success_count=0
failed_count=0

while IFS=$'\t' read -r team_id slug title author; do
    [[ -n "${team_id:-}" ]] || continue
    [[ "$team_id" == \#* ]] && continue

    api_url="https://teams.pokemonshowdown.com/api/getteam?teamid=${team_id}&full=1"
    json_file="$ROOT_DIR/.runtime/bss-team-${team_id}.json"
    packed_file="$ROOT_DIR/.runtime/bss-team-${team_id}.packed"
    export_file="$TEMP_DIR/${slug}.txt"

    echo "Fetching $title by $author..."
    if ! curl -fsSL --retry 3 --retry-delay 2 --connect-timeout 15 --max-time 45 \
        "$api_url" -o "$json_file"; then
        echo "Warning: failed to download team $team_id." >&2
        failed_count=$((failed_count + 1))
        continue
    fi

    if ! python3 - "$json_file" "$packed_file" "$team_id" <<'PY'
import json
import pathlib
import sys

source = pathlib.Path(sys.argv[1])
target = pathlib.Path(sys.argv[2])
team_id = sys.argv[3]
raw = source.read_text(encoding="utf-8").strip()
if raw.startswith("]"):
    raw = raw[1:]
data = json.loads(raw)
if data.get("actionerror"):
    raise SystemExit(f"Team {team_id}: {data['actionerror']}")
if data.get("format") != "gen9bssregi":
    raise SystemExit(
        f"Team {team_id}: expected gen9bssregi, found {data.get('format')!r}"
    )
packed = data.get("team")
if not isinstance(packed, str) or not packed:
    raise SystemExit(f"Team {team_id}: packed team data is missing")
target.write_text(packed, encoding="utf-8")
PY
    then
        echo "Warning: invalid response for team $team_id." >&2
        failed_count=$((failed_count + 1))
        continue
    fi

    if ! node "$ROOT_DIR/pokemon-showdown" export-team < "$packed_file" > "$export_file"; then
        echo "Warning: could not export team $team_id." >&2
        rm -f "$export_file"
        failed_count=$((failed_count + 1))
        continue
    fi

    if ! node "$ROOT_DIR/pokemon-showdown" validate-team gen9bssregi < "$export_file" >/dev/null; then
        echo "Warning: team $team_id is no longer legal in gen9bssregi." >&2
        rm -f "$export_file"
        failed_count=$((failed_count + 1))
        continue
    fi

    success_count=$((success_count + 1))
done < "$MANIFEST"

if [[ "$success_count" -lt 3 ]]; then
    echo "Only $success_count BSS teams were prepared; refusing to replace the library." >&2
    exit 1
fi

rm -rf "$TARGET_DIR"
mv "$TEMP_DIR" "$TARGET_DIR"
trap - EXIT

printf '%s\n' "BSS team library updated: $success_count teams ready, $failed_count skipped."
