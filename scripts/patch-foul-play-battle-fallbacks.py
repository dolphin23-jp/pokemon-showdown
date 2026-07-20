#!/usr/bin/env python3
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
BSS_TARGET = ROOT / "foul-play" / "fp" / "modes" / "bss.py"
BASE_TARGET = ROOT / "foul-play" / "fp" / "modes" / "base.py"
PROTOCOL_TARGET = ROOT / "foul-play" / "fp" / "battle" / "protocol.py"
RUN_BATTLE_TARGET = ROOT / "foul-play" / "fp" / "run_battle.py"

BSS_MARKER = "PERSONAL_SERVER_BSS_PREVIEW_FALLBACK"
MOVE_MARKER = "PERSONAL_SERVER_MOVE_FALLBACK"
FORCE_SWITCH_MARKER = "PERSONAL_SERVER_FORCE_SWITCH_FALLBACK"
SPEED_MARKER = "PERSONAL_SERVER_SWITCH_SPEED_GUARD"
INFERENCE_MARKER = "PERSONAL_SERVER_OPTIONAL_INFERENCE_GUARD"
UPDATE_MARKER = "PERSONAL_SERVER_BATTLE_UPDATE_FALLBACK"

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

    # PERSONAL_SERVER_FORCE_SWITCH_FALLBACK
    # Forced-switch searches are a common failure and memory-spike point for
    # custom National Dex states. The team-preview order already ranks the two
    # reserves, so use the first living reserve without launching another MCTS.
    if (
        battle_copy.force_switch
        and FoulPlayConfig.pokemon_format == "gen9nationaldexallgenerationsbss"
    ):
        logger.warning("Forced switch in the personal format; using the next selected reserve")
        return _fallback_action_from_request(battle_copy)

    loop = asyncio.get_event_loop()
    try:
        with concurrent.futures.ThreadPoolExecutor() as pool:
            best_move = await loop.run_in_executor(pool, find_best_move, battle_copy)

        battle.user.last_selected_move = LastUsedMove(
            battle_copy.user.active.name,
            best_move.removesuffix("-tera").removesuffix("-mega"),
            battle.turn,
        )
        return format_decision(battle_copy, best_move)
    except Exception:
        # Search and decision formatting are both protected. National Dex switch
        # names and unsupported mechanics can fail after MCTS has already returned.
        logger.exception("Move search or decision formatting failed; using a legal fallback action")
        return _fallback_action_from_request(battle_copy)

'''

RUN_BATTLE_REPLACEMENT = '''async def pokemon_battle(ps_websocket_client, pokemon_battle_type, team_dict):
    battle = await start_battle(ps_websocket_client, pokemon_battle_type, team_dict)
    while True:
        msg = await ps_websocket_client.receive_message()
        if battle_is_finished(battle.battle_tag, msg):
            winner = (
                msg.split(constants.WIN_STRING)[-1].split("\\n")[0].strip()
                if constants.WIN_STRING in msg
                else None
            )
            logger.info("Winner: {}".format(winner))
            await ps_websocket_client.send_message(battle.battle_tag, ["gg"])
            if (
                FoulPlayConfig.save_replay == SaveReplay.always
                or (
                    FoulPlayConfig.save_replay == SaveReplay.on_loss
                    and winner != FoulPlayConfig.username
                )
                or (
                    FoulPlayConfig.save_replay == SaveReplay.on_win
                    and winner == FoulPlayConfig.username
                )
            ):
                await ps_websocket_client.save_replay(battle.battle_tag)
            await ps_websocket_client.leave_battle(battle.battle_tag)
            return winner

        try:
            action_required = await async_update_battle(battle, msg)
        except Exception:
            # PERSONAL_SERVER_BATTLE_UPDATE_FALLBACK
            # Optional inference and uncommon National Dex protocol combinations
            # must not terminate the WebSocket process. The request JSON is parsed
            # before queued battle events, so it remains sufficient for a legal
            # fallback move or forced switch.
            logger.exception("Battle-state update failed; continuing from the latest request")
            battle.msg_list.clear()
            action_required = bool(battle.request_json) and not battle.wait

        if action_required and not battle.wait:
            best_move = await async_pick_move(battle)
            await ps_websocket_client.send_message(battle.battle_tag, best_move)
'''

SPEED_NEEDLE = '''    moves = [get_move_information(m) for m in msg_lines if m.startswith("|move|")]
    number_of_moves = len(moves)

    if (
        number_of_moves == 1
'''
SPEED_REPLACEMENT = '''    moves = [get_move_information(m) for m in msg_lines if m.startswith("|move|")]
    number_of_moves = len(moves)

    # PERSONAL_SERVER_SWITCH_SPEED_GUARD
    # A Pokemon can faint while attempting to switch (Pursuit and custom-format
    # edge cases). A switch command is not a move ID and must never be indexed in
    # all_move_json during speed inference.
    if (
        number_of_moves == 1
        and getattr(battle.user.last_selected_move, "move", "").startswith("switch ")
    ):
        logger.warning("Skipping speed inference after a failed or interrupted switch")
        return

    if (
        number_of_moves == 1
'''

INFERENCE_NEEDLE = '''    check_speed_ranges(battle, msg_lines)
    for i, line in enumerate(msg_lines):
'''
INFERENCE_REPLACEMENT = '''    # PERSONAL_SERVER_OPTIONAL_INFERENCE_GUARD
    try:
        check_speed_ranges(battle, msg_lines)
    except Exception:
        logger.exception("Speed inference failed; continuing with core battle updates")
    for i, line in enumerate(msg_lines):
'''

DAMAGE_NEEDLE = '''        if action == "move" and is_opponent(battle, split_msg):
            if normalize_name(split_msg[3].strip()) == constants.HIDDEN_POWER:
                check_opponent_hiddenpower(battle, msg_lines[i + 1])
            check_choicescarf(battle, msg_lines)
            damage_dealt = get_damage_dealt(battle, split_msg, msg_lines[i + 1 :])
            if damage_dealt:
                update_dataset_possibilities(battle, damage_dealt, "damage_dealt")

        elif action == "move" and not is_opponent(battle, split_msg):
            damage_dealt = get_damage_dealt(battle, split_msg, msg_lines[i + 1 :])
            if damage_dealt:
                update_dataset_possibilities(battle, damage_dealt, "damage_received")

        elif action == "switch" and is_opponent(battle, split_msg):
            check_heavydutyboots(battle, msg_lines[i + 1 :])
'''
DAMAGE_REPLACEMENT = '''        try:
            if action == "move" and is_opponent(battle, split_msg):
                if normalize_name(split_msg[3].strip()) == constants.HIDDEN_POWER:
                    check_opponent_hiddenpower(battle, msg_lines[i + 1])
                check_choicescarf(battle, msg_lines)
                damage_dealt = get_damage_dealt(battle, split_msg, msg_lines[i + 1 :])
                if damage_dealt:
                    update_dataset_possibilities(battle, damage_dealt, "damage_dealt")

            elif action == "move" and not is_opponent(battle, split_msg):
                damage_dealt = get_damage_dealt(battle, split_msg, msg_lines[i + 1 :])
                if damage_dealt:
                    update_dataset_possibilities(battle, damage_dealt, "damage_received")

            elif action == "switch" and is_opponent(battle, split_msg):
                check_heavydutyboots(battle, msg_lines[i + 1 :])
        except Exception:
            logger.exception("Optional set inference failed; continuing the battle")
'''


def replace_method(source: str, start: str, end: str, replacement: str) -> str:
    start_index = source.find(start)
    if start_index < 0:
        raise SystemExit(f"Could not find patch start marker: {start!r}")
    end_index = source.find(end, start_index)
    if end_index < 0:
        raise SystemExit(f"Could not find patch end marker: {end!r}")
    return source[:start_index] + replacement + source[end_index:]


def replace_once(source: str, needle: str, replacement: str, label: str) -> str:
    if source.count(needle) != 1:
        raise SystemExit(f"Could not safely patch {label}; expected one match")
    return source.replace(needle, replacement, 1)


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
    if FORCE_SWITCH_MARKER in source:
        print("foul-play move and forced-switch fallbacks are already applied.")
        return
    patched = replace_method(
        source,
        "def _fallback_action_from_request(battle):\n"
        if MOVE_MARKER in source
        else "async def async_pick_move(battle):\n",
        "async def handle_team_preview(battle, ps_websocket_client):\n",
        BASE_REPLACEMENT,
    )
    BASE_TARGET.write_text(patched, encoding="utf-8")
    print("Applied foul-play move and forced-switch fallbacks.")


def patch_protocol() -> None:
    source = PROTOCOL_TARGET.read_text(encoding="utf-8")
    changed = False
    if SPEED_MARKER not in source:
        source = replace_once(source, SPEED_NEEDLE, SPEED_REPLACEMENT, "switch speed guard")
        changed = True
    if INFERENCE_MARKER not in source:
        source = replace_once(source, INFERENCE_NEEDLE, INFERENCE_REPLACEMENT, "speed inference guard")
        source = replace_once(source, DAMAGE_NEEDLE, DAMAGE_REPLACEMENT, "damage inference guard")
        changed = True
    if changed:
        PROTOCOL_TARGET.write_text(source, encoding="utf-8")
        print("Applied foul-play protocol inference guards.")
    else:
        print("foul-play protocol inference guards are already applied.")


def patch_run_battle() -> None:
    source = RUN_BATTLE_TARGET.read_text(encoding="utf-8")
    if UPDATE_MARKER in source:
        print("foul-play battle-update fallback is already applied.")
        return
    start = "async def pokemon_battle(ps_websocket_client, pokemon_battle_type, team_dict):\n"
    start_index = source.find(start)
    if start_index < 0:
        raise SystemExit("Could not find pokemon_battle for patching")
    RUN_BATTLE_TARGET.write_text(
        source[:start_index] + RUN_BATTLE_REPLACEMENT + "\n",
        encoding="utf-8",
    )
    print("Applied foul-play battle-update fallback.")


def main() -> None:
    for target in (BSS_TARGET, BASE_TARGET, PROTOCOL_TARGET, RUN_BATTLE_TARGET):
        if not target.is_file():
            raise SystemExit(f"foul-play source file was not found: {target}")
    patch_bss()
    patch_move_search()
    patch_protocol()
    patch_run_battle()


if __name__ == "__main__":
    main()
