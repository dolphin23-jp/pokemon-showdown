#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import re
import subprocess
import time
from typing import Any

import websockets

ROOT = pathlib.Path(__file__).resolve().parents[1]
FORMAT = "gen9nationaldexallgenerationsbss"
PLAYER = "ProtocolSmoke"
JAPANESE_TEXT = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uff66-\uff9f]")


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
        raise RuntimeError(f"Could not pack protocol invariant team: {result.stderr}")
    return result.stdout.strip()


def require_canonical_text(label: str, value: str) -> None:
    if JAPANESE_TEXT.search(value):
        raise AssertionError(f"{label} contains Japanese display text: {value}")


def validate_request(line: str) -> dict[str, Any]:
    require_canonical_text("raw |request| protocol", line)
    payload = line[len("|request|"):]
    request = json.loads(payload)
    if json.dumps(request, ensure_ascii=False, separators=(",", ":")) != payload:
        reparsed = json.loads(payload)
        if reparsed != request:
            raise AssertionError("Raw |request| JSON did not round-trip without semantic changes")

    for active in request.get("active", []):
        for move in active.get("moves", []):
            move_name = str(move.get("move", ""))
            move_id = str(move.get("id", ""))
            require_canonical_text("request move name", move_name)
            require_canonical_text("request move id", move_id)
            if move_name and move_id != to_id(move_name):
                raise AssertionError(
                    f"Request move ID is not the canonical normalized English name: {move_name} -> {move_id}"
                )

    for pokemon in request.get("side", {}).get("pokemon", []):
        for key in ("ident", "details", "baseAbility", "item"):
            require_canonical_text(f"request side pokemon {key}", str(pokemon.get(key, "")))
        for move_id in pokemon.get("moves", []):
            require_canonical_text("request side move ID", str(move_id))

    return request


def first_legal_move(request: dict[str, Any]) -> int | None:
    active = request.get("active", [])
    if not active:
        return None
    for index, move in enumerate(active[0].get("moves", []), 1):
        if not move.get("disabled"):
            return index
    return None


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
                raise RuntimeError(f"Protocol smoke player could not claim its name: {line}")
    raise TimeoutError("Protocol smoke player could not log in")


async def verify_japanese_translations(websocket, deadline: float) -> None:
    await websocket.send('|/updatesettings {"language":"japanese"}')
    await websocket.send("|/language")
    while time.monotonic() < deadline:
        message = await asyncio.wait_for(
            websocket.recv(), timeout=max(0.1, deadline - time.monotonic())
        )
        if "現在、Pokémon Showdownを" in message:
            return
    raise TimeoutError("Japanese server language setting was not confirmed")


async def run_smoke(
    bot_name: str,
    port: int,
    timeout: float,
    output: pathlib.Path | None = None,
) -> None:
    uri = f"ws://127.0.0.1:{port}/showdown/websocket"
    deadline = time.monotonic() + timeout
    history: list[str] = []
    critical_lines: dict[str, list[str]] = {
        "request": [],
        "switch": [],
        "move": [],
    }
    outbound_commands: list[str] = []

    async with websockets.connect(uri) as websocket:
        await wait_for_login(websocket, deadline)
        await verify_japanese_translations(websocket, deadline)
        await websocket.send(f"|/utm {packed_team()}")
        await websocket.send(f"|/challenge {bot_name},{FORMAT}")

        battle_room = ""
        sent_team = False
        sent_choose = False
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

                if line.startswith("|request|"):
                    request = validate_request(line)
                    critical_lines["request"].append(line)
                    rqid = int(request.get("rqid", 0))
                    if request.get("teamPreview") and not sent_team:
                        command = f"{battle_room}|/team 123456|{rqid}"
                        require_canonical_text("outbound /team command", command)
                        outbound_commands.append(command)
                        await websocket.send(command)
                        sent_team = True
                        continue

                    if sent_team and not sent_choose and not request.get("wait"):
                        move_index = first_legal_move(request)
                        if move_index is not None:
                            command = f"{battle_room}|/choose move {move_index}|{rqid}"
                            require_canonical_text("outbound /choose command", command)
                            if f"/choose move {move_index}" not in command:
                                raise AssertionError(f"Outbound choice was rewritten unexpectedly: {command}")
                            outbound_commands.append(command)
                            await websocket.send(command)
                            sent_choose = True
                    continue

                if line.startswith("|switch|"):
                    require_canonical_text("raw |switch| protocol", line)
                    critical_lines["switch"].append(line)
                    continue

                if line.startswith("|move|"):
                    require_canonical_text("raw |move| protocol", line)
                    critical_lines["move"].append(line)

                if line.startswith("|error|"):
                    raise RuntimeError(f"Pokemon Showdown battle error: {line}")

                if (
                    sent_choose
                    and critical_lines["request"]
                    and critical_lines["switch"]
                    and critical_lines["move"]
                ):
                    await websocket.send(f"{battle_room}|/forfeit")
                    report = {
                        "task": "Phase 1 T1-10",
                        "japanese_server_setting_confirmed": True,
                        "battle_room": battle_room,
                        "critical_protocol_types": ["|request|", "|switch|", "|move|"],
                        "request_lines_checked": len(critical_lines["request"]),
                        "switch_lines_checked": len(critical_lines["switch"]),
                        "move_lines_checked": len(critical_lines["move"]),
                        "outbound_commands": outbound_commands,
                        "choose_command_unchanged": any("|/choose move " in command for command in outbound_commands),
                        "raw_protocol_contains_japanese_display_names": False,
                        "verified": True,
                    }
                    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
                    if output:
                        output.parent.mkdir(parents=True, exist_ok=True)
                        output.write_text(payload, encoding="utf-8")
                    print(payload, end="")
                    return

    excerpt = "\n---\n".join(history[-12:])
    raise TimeoutError(
        "Protocol invariant smoke did not observe request, switch, move, and /choose coverage. "
        f"Recent protocol:\n{excerpt}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bot", default="FoulPlayAI")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--timeout", type=float, default=90)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    asyncio.run(run_smoke(args.bot, args.port, args.timeout, args.output))


if __name__ == "__main__":
    main()
