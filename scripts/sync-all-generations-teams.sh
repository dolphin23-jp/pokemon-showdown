#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/.runtime"
FALLBACK_DIR="$ROOT_DIR/config/all-generations-fallback"
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
# Never perform a slow community search during a normal Render cold start.
if [[ "$REFRESH" -eq 0 && "$existing_count" -ge 3 && -f "$METADATA_FILE" ]]; then
    echo "All-generations team library is ready ($existing_count teams)."
    exit 0
fi

if [[ ! -d "$FALLBACK_DIR" ]]; then
    echo "Embedded all-generations fallback teams are missing: $FALLBACK_DIR" >&2
    exit 1
fi

mkdir -p "$RUNTIME_DIR/bss-teams"
TEMP_DIR="$(mktemp -d "$RUNTIME_DIR/bss-teams/.all-generations.XXXXXX")"
TEMP_METADATA="$TEMP_DIR/metadata.tsv"
trap 'rm -rf "$TEMP_DIR"' EXIT

python3 - "$ROOT_DIR" "$FALLBACK_DIR" "$BSS_DIR" "$TEMP_DIR" "$TEMP_METADATA" "$FORMAT" "$LIMIT" <<'PY'
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess
import sys
import urllib.parse
import urllib.request

root = pathlib.Path(sys.argv[1])
fallback_dir = pathlib.Path(sys.argv[2])
bss_dir = pathlib.Path(sys.argv[3])
out_dir = pathlib.Path(sys.argv[4])
metadata_path = pathlib.Path(sys.argv[5])
format_id = sys.argv[6]
limit = max(12, int(sys.argv[7]))
showdown = root / "pokemon-showdown"
manifest = root / "config" / "bss-team-sources.tsv"

records: list[tuple[str, str, str, str, str]] = []
seen: set[str] = set()
rejection_messages = 0


def clean_field(value: object, fallback: str) -> str:
    cleaned = re.sub(r"[\t\r\n]+", " ", str(value or fallback)).strip()
    return cleaned or fallback


def slugify(value: str, fallback: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value[:64] or fallback


def title_from_filename(team_file: pathlib.Path) -> str:
    name = re.sub(r"^\d+-", "", team_file.stem)
    return name.replace("-", " ").title()


def run_showdown(command: str, text: str) -> subprocess.CompletedProcess[str]:
    args = ["node", str(showdown), command]
    if command == "validate-team":
        args.append(format_id)
    return subprocess.run(
        args,
        input=text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=root,
        timeout=90,
    )


def looks_exported(team_text: str) -> bool:
    return (
        "\n" in team_text and
        re.search(r"(?m)^Ability:\s*\S", team_text) is not None and
        re.search(r"(?m)^-\s+\S", team_text) is not None
    )


def report_rejection(label: str, process: subprocess.CompletedProcess[str] | None = None) -> None:
    global rejection_messages
    if rejection_messages >= 8:
        return
    details = ""
    if process is not None:
        details = (process.stdout + "\n" + process.stderr).strip()
    print(f"Skipping {label}: {details or 'incompatible team data'}", file=sys.stderr)
    rejection_messages += 1


def normalize_export(team_text: str, label: str) -> str | None:
    raw = team_text.strip()
    if not raw:
        report_rejection(label)
        return None

    # Repository-owned fallback teams and downloaded BSS seeds are already in
    # Showdown Import/Export form. Community API responses are normally packed.
    # Only packed strings should be passed through `export-team`.
    if looks_exported(raw):
        text = raw
    else:
        exported = run_showdown("export-team", raw)
        if exported.returncode != 0 or not exported.stdout.strip():
            report_rejection(label, exported)
            return None
        text = exported.stdout.strip()

    # foul-play currently does not support Z-Moves or Dynamax.
    if re.search(r"@\s+.*ium Z(?:\s|$)", text, re.IGNORECASE):
        report_rejection(label)
        return None
    if "Dynamax Level:" in text or "Gigantamax: Yes" in text:
        report_rejection(label)
        return None

    members = [block for block in re.split(r"\n\s*\n", text) if block.strip()]
    if len(members) != 6:
        report_rejection(label)
        return None

    validated = run_showdown("validate-team", text)
    if validated.returncode != 0:
        report_rejection(label, validated)
        return None
    return text + "\n"


def add_team(team_id: str, title: str, author: str, packed_or_exported: str, source: str) -> bool:
    normalized = normalize_export(packed_or_exported, title)
    if normalized is None:
        return False
    digest = hashlib.sha256(normalized.encode()).hexdigest()
    if digest in seen:
        return False
    seen.add(digest)
    team_id = clean_field(team_id, "community")
    title = clean_field(title, f"Community team {team_id}")
    author = clean_field(author, "Pokemon Showdown community")
    source = clean_field(source, "community")
    slug = slugify(title, f"team-{team_id}")
    candidate = slug
    suffix = 2
    while (out_dir / f"{candidate}.txt").exists():
        candidate = f"{slug}-{suffix}"
        suffix += 1
    (out_dir / f"{candidate}.txt").write_text(normalized, encoding="utf-8")
    records.append((team_id, candidate, title, author, source))
    return True


# These repository-owned teams guarantee that Docker builds do not depend on a
# public API being reachable.
for team_file in sorted(fallback_dir.glob("*.txt")):
    add_team(
        f"embedded-{team_file.stem}",
        title_from_filename(team_file),
        "Personal AI Library",
        team_file.read_text(encoding="utf-8"),
        "embedded",
    )

# If the curated Regulation I library is already present, include it too.
seed_meta: dict[str, tuple[str, str, str]] = {}
if manifest.exists():
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        team_id, slug, title, author, *_ = line.split("\t")
        seed_meta[slug] = (team_id, title, author)
if bss_dir.exists():
    for team_file in sorted(bss_dir.glob("*.txt")):
        fallback = (f"seed-{team_file.stem}", team_file.stem, "BSS Sample Teams")
        team_id, title, author = seed_meta.get(team_file.stem, fallback)
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


# Search several public National Dex pools for variety, then validate each team
# against the embedded all-generations format before making it selectable.
for source_format in ("gen9nationaldexag", "gen9nationaldexubers", "gen9nationaldex"):
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

# Keep metadata outside the team folder because foul-play treats every regular
# file in that folder as a possible team.
mv "$TEMP_METADATA" "$RUNTIME_DIR/bss-teams/.all-generations-metadata.tsv"
rm -rf "$TARGET_DIR"
mv "$TEMP_DIR" "$TARGET_DIR"
mv "$RUNTIME_DIR/bss-teams/.all-generations-metadata.tsv" "$METADATA_FILE"
trap - EXIT

team_count="$(find "$TARGET_DIR" -maxdepth 1 -type f -name '*.txt' | wc -l | tr -d ' ')"
echo "All-generations team library updated: $team_count teams ready."
