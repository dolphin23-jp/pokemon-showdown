#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import pathlib
import re
import sys
import tempfile
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
FOUL_PLAY_ROOT = ROOT / "foul-play"
TARGET = FOUL_PLAY_ROOT / "fp" / "search" / "main.py"
JAPANESE_TEXT = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uff66-\uff9f]")


def real_pokemon(Pokemon, name: str, ability: str, item: str, moves: list[str]):
    pokemon = Pokemon(name, 50)
    pokemon.ability = ability
    pokemon.original_ability = ability
    pokemon.item = item
    for move in moves:
        pokemon.add_move(move)
    return pokemon


def main() -> None:
    source = TARGET.read_text(encoding="utf-8")
    required_markers = [
        "PERSONAL_SERVER_POKE_ENGINE_BOUNDARY_LOG",
        'os.environ.get("FOUL_PLAY_POKE_ENGINE_BOUNDARY_LOG")',
        '"serialized_state": serialized_state',
        '"rust_state": poke_engine_state.to_string()',
        '"snapshot": _poke_engine_state_snapshot(poke_engine_state)',
        "monte_carlo_tree_search(poke_engine_state",
    ]
    missing = [marker for marker in required_markers if marker not in source]
    if missing:
        raise AssertionError(f"Poke-engine boundary instrumentation markers are missing: {missing}")

    sys.path.insert(0, str(FOUL_PLAY_ROOT))
    from fp.battle.state import Battle, Pokemon
    from fp.modes.standard_battle import StandardBattleMode
    from fp.search import main as search_main
    from fp.search.poke_engine_helpers import battle_to_poke_engine_state

    battle = Battle(None)
    battle.generation = "gen9"
    battle.mode = StandardBattleMode()
    battle.user.active = real_pokemon(
        Pokemon,
        "pikachu",
        "static",
        "lightball",
        ["thunderbolt", "surf"],
    )
    battle.opponent.active = real_pokemon(
        Pokemon,
        "garchomp",
        "roughskin",
        "rockyhelmet",
        ["earthquake"],
    )

    engine_state = battle_to_poke_engine_state(battle)
    serialized_state = engine_state.to_string()

    with tempfile.TemporaryDirectory() as temp_dir:
        log_path = pathlib.Path(temp_dir) / "poke-engine-boundary.jsonl"
        with mock.patch.dict(
            os.environ,
            {"FOUL_PLAY_POKE_ENGINE_BOUNDARY_LOG": str(log_path)},
            clear=False,
        ):
            search_main._write_poke_engine_boundary_log(
                serialized_state,
                engine_state,
                7,
            )

        records = [
            json.loads(line)
            for line in log_path.read_text(encoding="utf-8").splitlines()
            if line
        ]
        if len(records) != 1:
            raise AssertionError(f"Expected one boundary record, found {len(records)}")
        record = records[0]
        if record["serialized_state"] != serialized_state:
            raise AssertionError("The serialized foul-play state changed before the Rust boundary")
        if record["rust_state"] != serialized_state:
            raise AssertionError("The Rust-backed State did not round-trip exactly")
        if record["search_index"] != 7:
            raise AssertionError("The boundary audit lost the MCTS search index")
        if not isinstance(record["recorded_at_ns"], int):
            raise AssertionError("The boundary audit is missing its integer timestamp")

        pokemon_records = record["snapshot"]["side_one"]
        pikachu = next((pokemon for pokemon in pokemon_records if pokemon["id"] == "pikachu"), None)
        if pikachu is None:
            raise AssertionError("The Rust boundary snapshot did not preserve pikachu")
        expected = {
            "id": "pikachu",
            "ability": "static",
            "base_ability": "static",
            "item": "lightball",
        }
        for key, value in expected.items():
            if pikachu[key] != value:
                raise AssertionError(f"Rust boundary changed {key}: {pikachu[key]!r}")
        if "thunderbolt" not in pikachu["moves"]:
            raise AssertionError("Rust boundary changed thunderbolt")

        serialized_record = json.dumps(record, ensure_ascii=False)
        if JAPANESE_TEXT.search(serialized_record):
            raise AssertionError("Japanese display text reached the Rust boundary unit fixture")

        with mock.patch.dict(os.environ, {}, clear=True):
            search_main._write_poke_engine_boundary_log(
                serialized_state,
                engine_state,
                8,
            )
        if len(log_path.read_text(encoding="utf-8").splitlines()) != 1:
            raise AssertionError(
                "Poke-engine boundary logging was not disabled when the environment variable was absent"
            )

    print(
        json.dumps(
            {
                "task": "Phase 1 T1-12",
                "boundary": "foul-play -> Rust poke-engine",
                "serialized_state_round_trip": True,
                "normalized_ids": {
                    "species": "pikachu",
                    "move": "thunderbolt",
                    "ability": "static",
                    "item": "lightball",
                },
                "jsonl_recording_opt_in": True,
                "default_runtime_unchanged": True,
                "japanese_ids_allowed": False,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
