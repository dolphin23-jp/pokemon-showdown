#!/usr/bin/env python3
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE_TARGET = ROOT / "foul-play" / "fp" / "modes" / "base.py"
INFERENCE_TARGET = ROOT / "foul-play" / "fp" / "battle" / "inference.py"
PROTOCOL_TARGET = ROOT / "foul-play" / "fp" / "battle" / "protocol.py"
RUN_BATTLE_TARGET = ROOT / "foul-play" / "fp" / "run_battle.py"

FORCE_SWITCH_MARKER = "PERSONAL_SERVER_FORCE_SWITCH_FALLBACK"
SPEED_MARKER = "PERSONAL_SERVER_SWITCH_SPEED_GUARD"
INFERENCE_MARKER = "PERSONAL_SERVER_OPTIONAL_INFERENCE_GUARD"
UPDATE_MARKER = "PERSONAL_SERVER_BATTLE_UPDATE_FALLBACK"

ASYNC_PICK_REPLACEMENT = '''async def async_pick_move(battle):
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
            # The current request is parsed before queued protocol events. Keep
            # the WebSocket alive and make a legal request-based decision even
            # when optional inference or an uncommon National Dex event fails.
            logger.exception("Battle-state update failed; continuing from the latest request")
            battle.msg_list.clear()
            action_required = bool(battle.request_json) and not battle.wait

        if action_required and not battle.wait:
            best_move = await async_pick_move(battle)
            await ps_websocket_client.send_message(battle.battle_tag, best_move)
'''

SPEED_NEEDLE = '''    moves = [get_move_information(m) for m in msg_lines if m.startswith("|move|")]
    number_of_moves = len(moves)
    if number_of_moves not in [1, 2]:
        return
'''
SPEED_REPLACEMENT = '''    moves = [get_move_information(m) for m in msg_lines if m.startswith("|move|")]
    number_of_moves = len(moves)
    if number_of_moves not in [1, 2]:
        return

    # PERSONAL_SERVER_SWITCH_SPEED_GUARD
    # A switch command is not a move ID. Pursuit and custom-format edge cases
    # can faint a Pokemon after it selected a switch, so skip speed inference.
    if (
        number_of_moves == 1
        and getattr(battle.user.last_selected_move, "move", "").startswith("switch ")
    ):
        logger.warning("Skipping speed inference after an interrupted switch")
        return
'''

PROTOCOL_SPEED_NEEDLE = '''    check_speed_ranges(battle, msg_lines)
    for i, line in enumerate(msg_lines):
'''
PROTOCOL_SPEED_REPLACEMENT = '''    # PERSONAL_SERVER_OPTIONAL_INFERENCE_GUARD
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


def replace_once(source: str, needle: str, replacement: str, label: str) -> str:
    if source.count(needle) != 1:
        raise SystemExit(f"Could not safely patch {label}; expected one match")
    return source.replace(needle, replacement, 1)


def replace_method(source: str, start: str, end: str, replacement: str) -> str:
    start_index = source.find(start)
    if start_index < 0:
        raise SystemExit(f"Could not find patch start marker: {start!r}")
    end_index = source.find(end, start_index)
    if end_index < 0:
        raise SystemExit(f"Could not find patch end marker: {end!r}")
    return source[:start_index] + replacement + source[end_index:]


def patch_forced_switch() -> None:
    source = BASE_TARGET.read_text(encoding="utf-8")
    if FORCE_SWITCH_MARKER in source:
        print("foul-play forced-switch fallback is already applied.")
        return
    patched = replace_method(
        source,
        "async def async_pick_move(battle):\n",
        "async def handle_team_preview(battle, ps_websocket_client):\n",
        ASYNC_PICK_REPLACEMENT,
    )
    BASE_TARGET.write_text(patched, encoding="utf-8")
    print("Applied foul-play forced-switch fallback.")


def patch_speed_inference() -> None:
    source = INFERENCE_TARGET.read_text(encoding="utf-8")
    if SPEED_MARKER in source:
        print("foul-play interrupted-switch speed guard is already applied.")
        return
    INFERENCE_TARGET.write_text(
        replace_once(source, SPEED_NEEDLE, SPEED_REPLACEMENT, "switch speed guard"),
        encoding="utf-8",
    )
    print("Applied foul-play interrupted-switch speed guard.")


def patch_protocol_inference() -> None:
    source = PROTOCOL_TARGET.read_text(encoding="utf-8")
    if INFERENCE_MARKER in source:
        print("foul-play optional inference guards are already applied.")
        return
    source = replace_once(
        source,
        PROTOCOL_SPEED_NEEDLE,
        PROTOCOL_SPEED_REPLACEMENT,
        "protocol speed inference guard",
    )
    source = replace_once(source, DAMAGE_NEEDLE, DAMAGE_REPLACEMENT, "damage inference guard")
    PROTOCOL_TARGET.write_text(source, encoding="utf-8")
    print("Applied foul-play optional inference guards.")


def patch_battle_loop() -> None:
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
    for target in (BASE_TARGET, INFERENCE_TARGET, PROTOCOL_TARGET, RUN_BATTLE_TARGET):
        if not target.is_file():
            raise SystemExit(f"foul-play source file was not found: {target}")
    patch_forced_switch()
    patch_speed_inference()
    patch_protocol_inference()
    patch_battle_loop()


if __name__ == "__main__":
    main()
