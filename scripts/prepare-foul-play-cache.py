#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
FOUL_PLAY_DATA = ROOT / "foul-play" / "fp" / "data"
FORMAT = "gen9nationaldexallgenerationsbss"
STATS_FORMAT = "gen9nationaldexubers"


def previous_month(today: dt.date, delta: int) -> tuple[int, int]:
    year = today.year
    month = today.month - delta
    while month <= 0:
        month += 12
        year -= 1
    return year, month


def cache_smogon_stats() -> None:
    cache_dir = FOUL_PLAY_DATA / "smogon_stats_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / f"{STATS_FORMAT}-0.json"
    today = dt.datetime.now(dt.timezone.utc).date()

    for delta in (1, 2, 3):
        year, month = previous_month(today, delta)
        url = f"https://www.smogon.com/stats/{year}-{month:02d}/chaos/{STATS_FORMAT}-0.json"
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Pokemon-Showdown-AI-Cache/1.0"})
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = json.load(response)
            data = payload.get("data")
            if not isinstance(data, dict) or not data:
                raise ValueError("statistics response has no data object")
            target.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
            print(f"Cached foul-play inference data from {url}")
            return
        except Exception as error:
            print(f"Warning: could not cache {url}: {error}", file=sys.stderr)

    print("Warning: no Smogon inference data was cached; foul-play will retry at runtime.", file=sys.stderr)


def create_empty_custom_dataset_cache() -> None:
    # foul-play's replay-dataset host has no files under our private format ID.
    # Empty cache files prevent repeated 404 requests; Smogon usage data remains
    # available for opponent-set inference.
    directory = FOUL_PLAY_DATA / "pkmn_sets_cache" / FORMAT
    directory.mkdir(parents=True, exist_ok=True)
    for filename in ("showdown_sets.json", "pokemon_full_sets.json", "replay_moves.json"):
        target = directory / filename
        if not target.exists():
            target.write_text("{}", encoding="utf-8")


if __name__ == "__main__":
    create_empty_custom_dataset_cache()
    cache_smogon_stats()
