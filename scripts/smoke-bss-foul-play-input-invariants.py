#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import pathlib
import re
import subprocess
import time
from typing import Any

import websockets

ROOT = pathlib.Path(__file__).resolve().parents[1]
FORMAT = "gen9nationaldexallgenerationsbss"
PLAYER = "BotInputSmoke"
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
        raise RuntimeError(f"Could not pack foul-play input smoke team: {result.stderr}")
    return result.stdout.strip()


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
                raise RuntimeError(f"Foul-play input smoke player could not claim its name: {line}")
    raise TimeoutError("Foul-play input smoke player could not log in")


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


def read_new_records(path: pathlib.Path, offset: int) -> list[dict[str, Any]]:
    with path.open("rb") as stream:
        stream.seek(offset)
        raw_payload = stream.read()
    if not raw_payload:
        return []

    # The Bot appends and closes one JSONL record per received frame. A reader
    # can still race the final write, so defer an incomplete trailing record
    # until the next polling iteration instead of treating it as corruption.
    if not raw_payload.endswith(b"\n"):
        if b"\n" not in raw_payload:
            return []
        raw_payload = raw_payload.rsplit(b"\n", 1)[0] + b"\n"

    payload = raw_payload.decode("utf-8")
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(payload.splitlines(), 1):
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise AssertionError(
                f"Invalid foul-play raw receive JSONL record at appended line {line_number}: {error}"
            ) from error
        if not isinstance(record, dict) or not isinstance(record.get("message"), str):
            raise AssertionError(f"Malformed foul-play raw receive record: {record!r}")
        records.append(record)
    return records


def battle_messages(records: list[dict[str, Any]], battle_room: str) -> list[str]:
    marker = f">{battle_room}"
    return [
        str(record["message"])
        for record in records
        if marker in str(record["message"])
    ]


def inspect_bot_requests(messages: list[str], battle_room: str) -> dict[str, Any]:
    category_values: dict[str, set[str]] = {
        "species": set(),
        "moves": set(),
        "abilities": set(),
        "items": set(),
    }
    protocol_counts = {"request": 0, "switch": 0, "move": 0}
    japanese_frames: list[str] = []

    for message in messages:
        if JAPANESE_TEXT.search(message):
            japanese_frames.append(message)
        for room, line in protocol_lines(message):
            if room != battle_room:
                continue
            if line.startswith("|request|"):
                protocol_counts["request"] += 1
                request = json.loads(line[len("|request|"):])
                for active in request.get("active", []):
                    for move in active.get("moves", []):
                        move_name = str(move.get("move", ""))
                        move_id = str(move.get("id", ""))
                        if move_name:
                            category_values["moves"].add(move_name)
                        if move_id:
                            category_values["moves"].add(move_id)
                        if move_name and move_id != to_id(move_name):
                            raise AssertionError(
                                f"Bot received a noncanonical move mapping: {move_name} -> {move_id}"
                            )
                for pokemon in request.get("side", {}).get("pokemon", []):
                    ident = str(pokemon.get("ident", ""))
                    details = str(pokemon.get("details", ""))
                    ability = str(pokemon.get("baseAbility", ""))
                    item = str(pokemon.get("item", ""))
                    if ident:
                        category_values["species"].add(ident)
                    if details:
                        category_values["species"].add(details)
                    if ability:
                        category_values["abilities"].add(ability)
                    if item:
                        category_values["items"].add(item)
                    for move_id in pokemon.get("moves", []):
                        category_values["moves"].add(str(move_id))
            elif line.startswith("|switch|"):
                protocol_counts["switch"] += 1
                fields = line.split("|")
                if len(fields) > 3:
                    category_values["species"].add(fields[3])
            elif line.startswith("|move|"):
                protocol_counts["move"] += 1
                fields = line.split("|")
                if len(fields) > 3:
                    category_values["moves"].add(fields[3])

    if japanese_frames:
        excerpt = "\n---\n".join(japanese_frames[:3])
        raise AssertionError(
            "Japanese text reached foul-play's battle-scoped raw WebSocket input:\n"
            + excerpt
        )

    missing_categories = [
        category
        for category, values in category_values.items()
        if not {value for value in values if value}
    ]
    if missing_categories:
        raise AssertionError(
            f"Foul-play raw input did not cover required categories: {missing_categories}"
        )
    if protocol_counts["request"] < 1:
        raise AssertionError("Foul-play raw input did not contain a |request| frame")
    if protocol_counts["switch"] < 1:
        raise AssertionError("Foul-play raw input did not contain a |switch| frame")
    if protocol_counts["move"] < 1:
        raise AssertionError("Foul-play raw input did not contain a |move| frame")

    for category, values in category_values.items():
        for value in values:
            if JAPANESE_TEXT.search(value):
                raise AssertionError(
                    f"Japanese {category} value reached foul-play: {value}"
                )

    return {
        "protocol_counts": protocol_counts,
        "category_coverage": {
            category: sorted(values)
            for category, values in category_values.items()
        },
    }


async def wait_for_bot_log(
    path: pathlib.Path,
    offset: int,
    battle_room: str,
    deadline: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    last_error: AssertionError | None = None
    while time.monotonic() < deadline:
        records = read_new_records(path, offset)
        messages = battle_messages(records, battle_room)
        if messages:
            try:
                inspection = inspect_bot_requests(messages, battle_room)
                return records, inspection
            except AssertionError as error:
                last_error = error
        await asyncio.sleep(0.25)
    if last_error:
        raise last_error
    raise TimeoutError(
        f"No battle-scoped foul-play raw receive records were written for {battle_room}"
    )


async def run_smoke(
    bot_name: str,
    port: int,
    timeout: float,
    raw_log: pathlib.Path,
    output: pathlib.Path | None = None,
) -> None:
    if not raw_log.is_file():
        raise AssertionError(
            f"Foul-play raw receive log is missing; set FOUL_PLAY_RAW_RECEIVE_LOG: {raw_log}"
        )
    offset = raw_log.stat().st_size
    uri = f"ws://127.0.0.1:{port}/showdown/websocket"
    deadline = time.monotonic() + timeout
    history: list[str] = []

    async with websockets.connect(uri) as websocket:
        await wait_for_login(websocket, deadline)
        await verify_japanese_translations(websocket, deadline)
        await websocket.send(f"|/utm {packed_team()}")
        await websocket.send(f"|/challenge {bot_name},{FORMAT}")

        battle_room = ""
        sent_team = False
        sent_choose = False
        observed_move = False
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
                    request = json.loads(line[len("|request|"):])
                    rqid = int(request.get("rqid", 0))
                    if request.get("teamPreview") and not sent_team:
                        await websocket.send(f"{battle_room}|/team 123456|{rqid}")
                        sent_team = True
                        continue
                    if sent_team and not sent_choose and not request.get("wait"):
                        move_index = first_legal_move(request)
                        if move_index is not None:
                            await websocket.send(
                                f"{battle_room}|/choose move {move_index}|{rqid}"
                            )
                            sent_choose = True
                    continue
                if line.startswith("|move|"):
                    observed_move = True
                if line.startswith("|error|"):
                    raise RuntimeError(f"Pokemon Showdown battle error: {line}")

            if battle_room and sent_choose and observed_move:
                records, inspection = await wait_for_bot_log(
                    raw_log, offset, battle_room, deadline
                )
                await websocket.send(f"{battle_room}|/forfeit")
                report = {
                    "task": "Phase 1 T1-11",
                    "japanese_server_setting_confirmed": True,
                    "battle_room": battle_room,
                    "raw_log": str(raw_log),
                    "appended_raw_records_checked": len(records),
                    "battle_scoped_frames_checked": len(
                        battle_messages(records, battle_room)
                    ),
                    "bot_received_japanese_names": False,
                    **inspection,
                    "verified": True,
                }
                payload = json.dumps(
                    report, ensure_ascii=False, indent=2, sort_keys=True
                ) + "\n"
                if output:
                    output.parent.mkdir(parents=True, exist_ok=True)
                    output.write_text(payload, encoding="utf-8")
                print(payload, end="")
                return

    excerpt = "\n---\n".join(history[-12:])
    raise TimeoutError(
        "Foul-play input invariant smoke did not reach a completed first move. "
        f"Recent challenger protocol:\n{excerpt}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bot", default="FoulPlayAI")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--timeout", type=float, default=90)
    parser.add_argument(
        "--raw-log",
        type=pathlib.Path,
        default=pathlib.Path(
            os.environ.get(
                "FOUL_PLAY_RAW_RECEIVE_LOG",
                ROOT / ".runtime" / "foul-play-received.jsonl",
            )
        ),
    )
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    asyncio.run(
        run_smoke(args.bot, args.port, args.timeout, args.raw_log, args.output)
    )


if __name__ == "__main__":
    main()
