#!/usr/bin/env python3
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
TARGET = ROOT / "foul-play" / "fp" / "search" / "main.py"
MARKER = "PERSONAL_SERVER_POKE_ENGINE_BOUNDARY_LOG"
IMPORT_NEEDLE = """import logging
import random
from concurrent.futures import ProcessPoolExecutor
"""
IMPORT_REPLACEMENT = """import json
import logging
import os
import random
import time
from concurrent.futures import ProcessPoolExecutor
"""
FUNCTION_NEEDLE = """def get_result_from_mcts(
    state: str, search_time_ms: int, index: int, threads: int
) -> MctsResult:
    logger.debug("Calling with {} state: {}".format(index, state))
    poke_engine_state = PokeEngineState.from_string(state)

    res = monte_carlo_tree_search(poke_engine_state, search_time_ms, threads=threads)
"""
FUNCTION_REPLACEMENT = """def _poke_engine_pokemon_snapshot(pokemon):
    return {
        "id": str(pokemon.id),
        "ability": str(pokemon.ability),
        "base_ability": str(pokemon.base_ability),
        "item": str(pokemon.item),
        "moves": [str(move.id) for move in pokemon.moves],
    }


def _poke_engine_state_snapshot(state):
    return {
        "side_one": [
            _poke_engine_pokemon_snapshot(pokemon)
            for pokemon in state.side_one.pokemon
        ],
        "side_two": [
            _poke_engine_pokemon_snapshot(pokemon)
            for pokemon in state.side_two.pokemon
        ],
    }


def _write_poke_engine_boundary_log(serialized_state, poke_engine_state, index):
    # PERSONAL_SERVER_POKE_ENGINE_BOUNDARY_LOG
    # Capture the exact Rust-backed State after from_string() and immediately
    # before monte_carlo_tree_search(). Normal runtime is unchanged unless the
    # environment variable is set.
    boundary_log = os.environ.get("FOUL_PLAY_POKE_ENGINE_BOUNDARY_LOG")
    if not boundary_log:
        return

    record = {
        "recorded_at_ns": time.time_ns(),
        "search_index": index,
        "serialized_state": serialized_state,
        "rust_state": poke_engine_state.to_string(),
        "snapshot": _poke_engine_state_snapshot(poke_engine_state),
    }
    with open(boundary_log, "a", encoding="utf-8") as stream:
        stream.write(
            json.dumps(record, ensure_ascii=False, separators=(",", ":"))
            + "\\n"
        )


def get_result_from_mcts(
    state: str, search_time_ms: int, index: int, threads: int
) -> MctsResult:
    logger.debug("Calling with {} state: {}".format(index, state))
    poke_engine_state = PokeEngineState.from_string(state)
    _write_poke_engine_boundary_log(state, poke_engine_state, index)

    res = monte_carlo_tree_search(poke_engine_state, search_time_ms, threads=threads)
"""


def main() -> None:
    if not TARGET.is_file():
        raise SystemExit(f"foul-play search module was not found: {TARGET}")

    source = TARGET.read_text(encoding="utf-8")
    if MARKER in source:
        print("foul-play poke-engine boundary log patch is already applied.")
        return
    if source.count(IMPORT_NEEDLE) != 1:
        raise SystemExit(
            "The pinned foul-play search import block changed; refusing to apply an unsafe patch."
        )
    if source.count(FUNCTION_NEEDLE) != 1:
        raise SystemExit(
            "The pinned foul-play get_result_from_mcts implementation changed; "
            "refusing to apply an unsafe patch."
        )

    patched = source.replace(IMPORT_NEEDLE, IMPORT_REPLACEMENT)
    patched = patched.replace(FUNCTION_NEEDLE, FUNCTION_REPLACEMENT)
    compile(patched, str(TARGET), "exec")
    TARGET.write_text(patched, encoding="utf-8")
    print("Applied foul-play poke-engine boundary log patch.")


if __name__ == "__main__":
    main()
