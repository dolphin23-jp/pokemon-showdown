#!/usr/bin/env python3
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
BSS_TARGET = ROOT / "foul-play" / "fp" / "modes" / "bss.py"
BASE_TARGET = ROOT / "foul-play" / "fp" / "modes" / "base.py"
BSS_MARKER = "PERSONAL_SERVER_BSS_PREVIEW_FALLBACK"
MOVE_MARKER = "PERSONAL_SERVER_MOVE_FALLBACK"

BSS_REPLACEMENT = '''    async def handle_team_preview(self, battle, ps_websocket_client):
        battle_copy = deepcopy(battle)
        battle_copy.user.active = Pokemon.get_dummy()
        battle_copy.opponent.active = Pokemon.get_dummy()
        battle_copy.team_preview = True

        selected_pokemon = None
        opponent_affinities = {}
        try:
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as pool:
                (best_move, opponent_affinities) = await loop.run_in_executor(
                    pool, bss_team_preview, battle_copy
                )

            selected_names = best_move.split(",")
            if len(selected_names) != 3:
                raise ValueError(f"Expected three team-preview choices, got: {best_move}")

            remaining = list(battle.user.reserve)
            selected_pokemon = []
            for selected_name in selected_names:
                for index, pkmn in enumerate(remaining):
                    if pkmn.name == selected_name or pkmn.base_name == selected_name:
                        selected_pokemon.append(pkmn)
                        remaining.pop(index)
                        break
                else:
                    raise ValueError(
                        f"Could not match team-preview choice {selected_name} to the bot team"
                    )
        except Exception:
            # PERSONAL_SERVER_BSS_PREVIEW_FALLBACK
            # Custom/National Dex teams can contain species with little or no
            # usage data. Keep the battle alive even when MCTS cannot construct
            # a complete sampled opponent team.
            logger.exception(
                "BSS team-preview search failed; selecting the first three legal Pokemon"
            )
            selected_pokemon = list(battle.user.reserve[:3])

        if len(selected_pokemon) != 3:
            raise ValueError(
                f"Cannot start a pick-three battle with {len(selected_pokemon)} selected Pokemon"
            )

        for pkmn in battle.opponent.reserve:
            opponent_affinities.setdefault(pkmn.name, 1.0)
        battle.opponent_team_preview_affinities = opponent_affinities

        lead, reserve_1, reserve_2 = selected_pokemon
        selected_ids = {id(pkmn) for pkmn in selected_pokemon}
        remaining_pokemon = [
            pkmn for pkmn in battle.user.reserve if id(pkmn) not in selected_ids
        ]
        team_order = selected_pokemon + remaining_pokemon

        for pkmn in selected_pokemon:
            logger.debug(f"Bringing {pkmn.name}")
        logger.debug(f"Leading with {lead.name}")
        for pkmn in remaining_pokemon:
            logger.debug(f"Leaving behind {pkmn.name}")
            pkmn.hp = 0
            pkmn.name = "none"

        battle.user.last_selected_move = LastUsedMove(
            "teampreview", f"switch {lead.name}", battle.turn
        )
        logger.info(f"Team: {lead.name}, [{reserve_1.name}, {reserve_2.name}]")

        message = [
            "/team {}|{}".format(
                "".join(str(pkmn.index) for pkmn in team_order), battle.rqid
            )
        ]
        await ps_websocket_client.send_message(battle.battle_tag, message)

'''

BASE_REPLACEMENT = '''def _fallback_action_from_request(battle):
    # PERSONAL_SERVER_MOVE_FALLBACK
    # A private custom format can expose combinations missing from foul-play's
    # inference datasets or poke-engine. Prefer a legal ordinary action over
    # abandoning the battle when the search raises an exception.
    request = battle.request_json or {}
    rqid = str(battle.rqid)

    force_switch = request.get("forceSwitch", [])
    if force_switch and any(force_switch):
        for index, pkmn in enumerate(request.get("side", {}).get("pokemon", []), 1):
            condition = str(pkmn.get("condition", ""))
            if not pkmn.get("active") and not condition.startswith("0 fnt"):
                logger.warning(f"Fallback decision: switch {index}")
                return [f"/switch {index}", rqid]

    active = request.get("active", [])
    if active:
        for index, move in enumerate(active[0].get("moves", []), 1):
            if not move.get("disabled", False) and move.get("pp", 1) != 0:
                logger.warning(f"Fallback decision: move {index}")
                return [f"/choose move {index}", rqid]

    for index, pkmn in enumerate(request.get("side", {}).get("pokemon", []), 1):
        condition = str(pkmn.get("condition", ""))
        if not pkmn.get("active") and not condition.startswith("0 fnt"):
            logger.warning(f"Fallback decision: switch {index}")
            return [f"/switch {index}", rqid]

    logger.warning("Fallback decision: Pokemon Showdown default action")
    return ["/choose default", rqid]


async def async_pick_move(battle):
    battle_copy = deepcopy(battle)
    if not battle_copy.team_preview:
        battle_copy.user.update_from_request_json(battle_copy.request_json)

    loop = asyncio.get_event_loop()
    try:
        with concurrent.futures.ThreadPoolExecutor() as pool:
            best_move = await loop.run_in_executor(pool, find_best_move, battle_copy)
    except Exception:
        logger.exception("Move search failed; using the first legal fallback action")
        return _fallback_action_from_request(battle_copy)

    battle.user.last_selected_move = LastUsedMove(
        battle_copy.user.active.name,
        best_move.removesuffix("-tera").removesuffix("-mega"),
        battle.turn,
    )
    return format_decision(battle_copy, best_move)

'''


def replace_method(source: str, start: str, end: str, replacement: str) -> str:
    start_index = source.find(start)
    if start_index < 0:
        raise SystemExit(f"Could not find patch start marker: {start!r}")
    end_index = source.find(end, start_index)
    if end_index < 0:
        raise SystemExit(f"Could not find patch end marker: {end!r}")
    return source[:start_index] + replacement + source[end_index:]


def patch_bss() -> None:
    source = BSS_TARGET.read_text(encoding="utf-8")
    if BSS_MARKER in source:
        print("foul-play BSS preview fallback is already applied.")
        return
    patched = replace_method(
        source,
        "    async def handle_team_preview(self, battle, ps_websocket_client):\n",
        "    def prepare_battles(self, battle, num_battles):\n",
        BSS_REPLACEMENT,
    )
    BSS_TARGET.write_text(patched, encoding="utf-8")
    print("Applied foul-play BSS preview fallback.")


def patch_move_search() -> None:
    source = BASE_TARGET.read_text(encoding="utf-8")
    if MOVE_MARKER in source:
        print("foul-play move fallback is already applied.")
        return
    patched = replace_method(
        source,
        "async def async_pick_move(battle):\n",
        "async def handle_team_preview(battle, ps_websocket_client):\n",
        BASE_REPLACEMENT,
    )
    BASE_TARGET.write_text(patched, encoding="utf-8")
    print("Applied foul-play move fallback.")


def main() -> None:
    for target in (BSS_TARGET, BASE_TARGET):
        if not target.is_file():
            raise SystemExit(f"foul-play source file was not found: {target}")
    patch_bss()
    patch_move_search()


if __name__ == "__main__":
    main()
