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
PLAYER = "BattleSmoke"


def protocol_lines(message: str):
    room = ""
    for line in message.splitlines():
        if line.startswith(">"):
            room = line[1:].strip()
            continue
        if line.startswith("|"):
            yield room, line


def packed_team() -> str:
    team_file = ROOT / "config" / "bss-smoke-opponent.txt"
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
        raise RuntimeError(f"Could not pack smoke team: {result.stderr}")
    return result.stdout.strip()


async def wait_for_login(websocket, deadline: float) -> None:
    saw_challstr = False
    while time.monotonic() < deadline:
        message = await asyncio.wait_for(
            websocket.recv(), timeout=max(0.1, deadline - time.monotonic())
        )
        for _room, line in protocol_lines(message):
            if line.startswith("|challstr|") and not saw_challstr:
                saw_challstr = True
                await websocket.send(f"|/trn {PLAYER},0,")
            elif line.startswith(f"|updateuser|{PLAYER}|1|"):
                return
    raise TimeoutError("Smoke player could not log in")


async def run_smoke(bot_name: str, port: int, timeout: float) -> None:
    uri = f"ws://127.0.0.1:{port}/showdown/websocket"
    deadline = time.monotonic() + timeout
    history: list[str] = []

    async with websockets.connect(uri) as websocket:
        await wait_for_login(websocket, deadline)
        await websocket.send(f"|/utm {packed_team()}")
        await websocket.send(f"|/challenge {bot_name},{FORMAT}")

        battle_room = ""
        sent_team = False
        while time.monotonic() < deadline:
            message = await asyncio.wait_for(
                websocket.recv(), timeout=max(0.1, deadline - time.monotonic())
            )
            history.append(message)
            for room, line in protocol_lines(message):
                if room.startswith("battle-"):
                    battle_room = room

                if battle_room and room == battle_room and line.startswith("|request|"):
                    request = json.loads(line[len("|request|"):])
                    if not sent_team and request.get("teamPreview"):
                        rqid = request.get("rqid")
                        await websocket.send(f"{battle_room}|/team 123456|{rqid}")
                        sent_team = True

                if battle_room and room == battle_room and line == "|turn|1":
                    await websocket.send(f"{battle_room}|/forfeit")
                    print(f"BSS smoke battle reached turn 1 against {bot_name}.")
                    return

                if battle_room and room == battle_room and line.startswith("|error|"):
                    raise RuntimeError(f"Pokemon Showdown battle error: {line}")

                if battle_room and room == battle_room and line.startswith("|player|"):
                    fields = line.split("|")
                    if len(fields) >= 4 and not fields[3] and sent_team:
                        raise RuntimeError(f"A player left before turn 1: {line}")

    excerpt = "\n---\n".join(history[-10:])
    raise TimeoutError(f"BSS smoke battle did not reach turn 1. Recent protocol:\n{excerpt}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bot", default="FoulPlayAI")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--timeout", type=float, default=60)
    args = parser.parse_args()
    asyncio.run(run_smoke(args.bot, args.port, args.timeout))


if __name__ == "__main__":
    main()
