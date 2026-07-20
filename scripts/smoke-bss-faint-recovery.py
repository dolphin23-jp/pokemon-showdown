#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import subprocess
import time

import websockets

ROOT = pathlib.Path(__file__).resolve().parents[1]
FORMAT = "gen9nationaldexallgenerationsbss"
PLAYER = "FaintSmoke"


def to_id(value: str) -> str:
    return "".join(character.lower() for character in value if character.isalnum())


def protocol_lines(message: str):
    room = ""
    for line in message.splitlines():
        if line.startswith(">"):
            room = line[1:].strip()
            continue
        if line.startswith("|"):
            yield room, line


def packed_team() -> str:
    team_file = ROOT / "config" / "bss-faint-smoke-opponent.txt"
    result = subprocess.run(
        ["node", "pokemon-showdown", "pack-team"],
        cwd=ROOT,
        input=team_file.read_text(encoding="utf-8"),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError(f"Could not pack post-faint smoke team: {result.stderr}")
    return result.stdout.strip()


async def wait_for_login(websocket, deadline: float) -> None:
    sent_name = False
    while time.monotonic() < deadline:
        message = await asyncio.wait_for(
            websocket.recv(), timeout=max(0.1, deadline - time.monotonic())
        )
        for _room, line in protocol_lines(message):
            if line.startswith("|challstr|") and not sent_name:
                sent_name = True
                await websocket.send(f"|/trn {PLAYER},0,")
                continue
            fields = line.split("|")
            if (
                len(fields) >= 4
                and fields[1] == "updateuser"
                and to_id(fields[2]) == to_id(PLAYER)
            ):
                if fields[3] == "1":
                    return
                raise RuntimeError(f"Post-faint smoke player could not claim its name: {line}")
    raise TimeoutError("Post-faint smoke player could not log in")


def first_legal_switch(request: dict) -> int | None:
    for index, pokemon in enumerate(request.get("side", {}).get("pokemon", []), 1):
        condition = str(pokemon.get("condition", ""))
        if not pokemon.get("active") and not condition.startswith("0 fnt"):
            return index
    return None


async def run_smoke(bot_name: str, port: int, timeout: float) -> None:
    uri = f"ws://127.0.0.1:{port}/showdown/websocket"
    deadline = time.monotonic() + timeout
    history: list[str] = []

    async with websockets.connect(uri) as websocket:
        await wait_for_login(websocket, deadline)
        await websocket.send(f"|/utm {packed_team()}")
        await websocket.send(f"|/challenge {bot_name},{FORMAT}")

        battle_room = ""
        player_slot = ""
        bot_slot = ""
        sent_rqids: set[int] = set()
        terastallized = False
        bot_fainted = False
        bot_replaced = False
        faint_turn = 0
        current_turn = 0

        while time.monotonic() < deadline:
            message = await asyncio.wait_for(
                websocket.recv(), timeout=max(0.1, deadline - time.monotonic())
            )
            history.append(message)
            for room, line in protocol_lines(message):
                if room.startswith("battle-"):
                    battle_room = room

                if not battle_room or room != battle_room:
                    continue

                if line.startswith("|player|"):
                    fields = line.split("|")
                    if len(fields) >= 4:
                        slot, name = fields[2], fields[3]
                        if to_id(name) == to_id(PLAYER):
                            player_slot = slot
                        elif to_id(name) == to_id(bot_name):
                            bot_slot = slot
                        elif bot_slot and slot == bot_slot and not name:
                            raise RuntimeError("Bot left the battle after a Pokemon fainted")

                if line.startswith("|turn|"):
                    current_turn = int(line.split("|")[2])
                    if bot_replaced and current_turn > faint_turn:
                        await websocket.send(f"{battle_room}|/forfeit")
                        print(
                            f"Post-faint smoke passed: {bot_name} replaced its fainted lead "
                            f"and reached turn {current_turn}."
                        )
                        return

                if bot_slot and line.startswith(f"|faint|{bot_slot}a:"):
                    bot_fainted = True
                    faint_turn = current_turn

                if (
                    bot_fainted
                    and bot_slot
                    and line.startswith(f"|switch|{bot_slot}a:")
                ):
                    bot_replaced = True

                if line.startswith("|error|"):
                    raise RuntimeError(f"Pokemon Showdown battle error: {line}")

                if not line.startswith("|request|"):
                    continue
                request = json.loads(line[len("|request|"):])
                rqid = int(request.get("rqid", 0))
                if rqid in sent_rqids or request.get("wait"):
                    continue
                sent_rqids.add(rqid)

                if request.get("teamPreview"):
                    await websocket.send(f"{battle_room}|/team 123456|{rqid}")
                    continue

                if request.get("forceSwitch") and any(request["forceSwitch"]):
                    switch_index = first_legal_switch(request)
                    if switch_index is None:
                        raise RuntimeError("Smoke player was forced to switch with no legal reserve")
                    await websocket.send(f"{battle_room}|/switch {switch_index}|{rqid}")
                    continue

                active = request.get("active", [])
                if active:
                    command = "/choose move 1"
                    if active[0].get("canTerastallize") and not terastallized:
                        command += " terastallize"
                        terastallized = True
                    await websocket.send(f"{battle_room}|{command}|{rqid}")

                if current_turn >= 12 and not bot_fainted:
                    raise RuntimeError("Could not faint the bot's lead within 12 turns")

    excerpt = "\n---\n".join(history[-12:])
    raise TimeoutError(
        "Post-faint BSS smoke did not observe a replacement and later turn. "
        f"Recent protocol:\n{excerpt}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bot", default="FoulPlayAI")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--timeout", type=float, default=150)
    args = parser.parse_args()
    asyncio.run(run_smoke(args.bot, args.port, args.timeout))


if __name__ == "__main__":
    main()
