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
PLAYER = "EngineSmoke"
JAPANESE_TEXT = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uff66-\uff9f]")
TARGET_IDS = {
    "species": "pikachu",
    "move": "thunderbolt",
    "ability": "static",
    "item": "lightball",
}


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
        raise RuntimeError(f"Could not pack poke-engine boundary smoke team: {result.stderr}")
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
                raise RuntimeError(f"Poke-engine boundary smoke player could not claim its name: {line}")
    raise TimeoutError("Poke-engine boundary smoke player could not log in")


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
    if not path.is_file():
        return []
    with path.open("rb") as stream:
        stream.seek(offset)
        raw_payload = stream.read()
    if not raw_payload:
        return []
    if not raw_payload.endswith(b"\n"):
        if b"\n" not in raw_payload:
            return []
        raw_payload = raw_payload.rsplit(b"\n", 1)[0] + b"\n"

    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(raw_payload.decode("utf-8").splitlines(), 1):
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise AssertionError(
                f"Invalid poke-engine boundary JSONL record at appended line {line_number}: {error}"
            ) from error
        if not isinstance(record, dict):
            raise AssertionError(f"Malformed poke-engine boundary record: {record!r}")
        records.append(record)
    return records


def inspect_boundary_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    matching: list[dict[str, Any]] = []
    for record in records:
        record_text = json.dumps(record, ensure_ascii=False, sort_keys=True)
        if JAPANESE_TEXT.search(record_text):
            raise AssertionError(
                "Japanese display text reached the foul-play -> Rust poke-engine boundary: "
                + record_text[:1200]
            )

        serialized_state = record.get("serialized_state")
        rust_state = record.get("rust_state")
        if not isinstance(serialized_state, str) or not isinstance(rust_state, str):
            raise AssertionError(f"Boundary record is missing state strings: {record!r}")
        if serialized_state != rust_state:
            raise AssertionError(
                "The Rust-backed State changed during from_string()/to_string() round-trip"
            )

        snapshot = record.get("snapshot")
        if not isinstance(snapshot, dict):
            raise AssertionError(f"Boundary record is missing its Rust snapshot: {record!r}")
        pokemon = [
            entry
            for side in ("side_one", "side_two")
            for entry in snapshot.get(side, [])
            if isinstance(entry, dict)
        ]
        for entry in pokemon:
            if entry.get("id") != TARGET_IDS["species"]:
                continue
            moves = [str(move) for move in entry.get("moves", [])]
            if (
                entry.get("ability") == TARGET_IDS["ability"]
                and entry.get("item") == TARGET_IDS["item"]
                and TARGET_IDS["move"] in moves
            ):
                matching.append(
                    {
                        "search_index": record.get("search_index"),
                        "pokemon": entry,
                        "serialized_state_bytes": len(serialized_state.encode("utf-8")),
                    }
                )

    if not matching:
        raise AssertionError(
            "No Rust boundary state preserved pikachu/thunderbolt/static/lightball together"
        )

    target = matching[0]["pokemon"]
    forbidden_display_values = ["Pikachu", "Thunderbolt", "Static", "Light Ball"]
    target_text = json.dumps(target, ensure_ascii=False, sort_keys=True)
    leaked = [value for value in forbidden_display_values if value in target_text]
    if leaked:
        raise AssertionError(f"Display names reached the Rust boundary: {leaked}")

    return {
        "records_checked": len(records),
        "matching_records": len(matching),
        "target_ids": TARGET_IDS,
        "observed_target": target,
        "state_round_trip_exact": True,
        "rust_boundary_contains_japanese_names": False,
    }


async def wait_for_boundary_log(
    path: pathlib.Path,
    offset: int,
    deadline: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    last_error: AssertionError | None = None
    while time.monotonic() < deadline:
        records = read_new_records(path, offset)
        if records:
            try:
                return records, inspect_boundary_records(records)
            except AssertionError as error:
                last_error = error
        await asyncio.sleep(0.25)
    if last_error:
        raise last_error
    raise TimeoutError("No foul-play -> poke-engine boundary records were written")


async def run_smoke(
    bot_name: str,
    port: int,
    timeout: float,
    boundary_log: pathlib.Path,
    output: pathlib.Path | None = None,
) -> None:
    offset = boundary_log.stat().st_size if boundary_log.is_file() else 0
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
                    if request.get("teamPreview") and not sent_team:
                        rqid = int(request.get("rqid", 0))
                        await websocket.send(f"{battle_room}|/team 123456|{rqid}")
                        sent_team = True
                elif line.startswith("|error|"):
                    raise RuntimeError(f"Pokemon Showdown battle error: {line}")

            if battle_room and sent_team:
                records, inspection = await wait_for_boundary_log(
                    boundary_log,
                    offset,
                    deadline,
                )
                await websocket.send(f"{battle_room}|/forfeit")
                report = {
                    "task": "Phase 1 T1-12",
                    "boundary": "foul-play -> Rust poke-engine",
                    "japanese_server_setting_confirmed": True,
                    "battle_room": battle_room,
                    "boundary_log": str(boundary_log),
                    "appended_records_checked": len(records),
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
        "Poke-engine boundary smoke did not reach team preview and a Rust state. "
        f"Recent challenger protocol:\n{excerpt}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bot", default="EngineBoundaryBot")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument(
        "--boundary-log",
        type=pathlib.Path,
        default=pathlib.Path(
            os.environ.get(
                "FOUL_PLAY_POKE_ENGINE_BOUNDARY_LOG",
                ROOT / ".runtime" / "poke-engine-boundary.jsonl",
            )
        ),
    )
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    asyncio.run(
        run_smoke(
            args.bot,
            args.port,
            args.timeout,
            args.boundary_log,
            args.output,
        )
    )


if __name__ == "__main__":
    main()
