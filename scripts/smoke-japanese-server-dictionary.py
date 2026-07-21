#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import re
import time

import websockets

PLAYER = "JapaneseDictionarySmoke"
ROOM = "lobby"
JAPANESE_LANGUAGE_CONFIRMATION = "Pokémon Showdownは言語部屋以外の場所はJapaneseで表示されます。"
FAQ_MARKERS = (
    "ティア制度に関するよくある質問",
    "バッジに関するよくある質問",
)
USERLIST_PREFIX = "この部屋には"
ENGLISH_USERLIST = re.compile(r"There (?:is|are) .* users? in this room", re.IGNORECASE)


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


async def wait_for_login(websocket, deadline: float, history: list[str]) -> None:
    sent_name = False
    while time.monotonic() < deadline:
        message = await asyncio.wait_for(
            websocket.recv(), timeout=max(0.1, deadline - time.monotonic())
        )
        history.append(message)
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
                raise RuntimeError(f"Smoke user could not claim its name: {line}")
    raise TimeoutError("Smoke user could not log in")


async def run_smoke(port: int, timeout: float, output: pathlib.Path | None) -> None:
    uri = f"ws://127.0.0.1:{port}/showdown/websocket"
    deadline = time.monotonic() + timeout
    history: list[str] = []
    language_confirmed = False
    room_joined = False
    faq_confirmed = {marker: False for marker in FAQ_MARKERS}
    userlist_confirmed = False
    userlist_responses: list[str] = []

    async with websockets.connect(uri) as websocket:
        await wait_for_login(websocket, deadline, history)

        # The completion condition explicitly requires the public command, not
        # only the settings JSON shortcut used by the client bootstrap.
        await websocket.send("|/language japanese")
        await websocket.send(f"|/join {ROOM}")

        commands_sent = False
        while time.monotonic() < deadline:
            message = await asyncio.wait_for(
                websocket.recv(), timeout=max(0.1, deadline - time.monotonic())
            )
            history.append(message)

            if JAPANESE_LANGUAGE_CONFIRMATION in message or (
                "Pokémon Showdown" in message and "Japanese" in message and "表示されます" in message
            ):
                language_confirmed = True

            for room, line in protocol_lines(message):
                if room == ROOM and line.startswith("|init|chat"):
                    room_joined = True
                if room == ROOM and USERLIST_PREFIX in line:
                    userlist_responses.append(line)
                    if ENGLISH_USERLIST.search(line):
                        raise AssertionError(f"/userlist still returned direct English: {line}")
                    if PLAYER not in line:
                        raise AssertionError(f"/userlist did not include the logged-in user: {line}")
                    userlist_confirmed = True
                for marker in FAQ_MARKERS:
                    if marker in line:
                        faq_confirmed[marker] = True

            if room_joined and not commands_sent:
                await websocket.send(f"{ROOM}|/faq")
                await websocket.send(f"{ROOM}|/userlist")
                commands_sent = True

            if language_confirmed and room_joined and userlist_confirmed and all(faq_confirmed.values()):
                report = {
                    "task": "Phase 2 server dictionary live smoke",
                    "player": PLAYER,
                    "room": ROOM,
                    "language_command": "/language japanese",
                    "language_confirmed": True,
                    "commands_checked": ["/faq", "/userlist"],
                    "faq_markers": faq_confirmed,
                    "userlist_japanese_prefix": USERLIST_PREFIX,
                    "userlist_direct_english": False,
                    "userlist_responses_checked": len(userlist_responses),
                    "verified": True,
                }
                payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
                if output:
                    output.parent.mkdir(parents=True, exist_ok=True)
                    output.write_text(payload, encoding="utf-8")
                print(payload, end="")
                return

    excerpt = "\n---\n".join(history[-15:])
    missing = {
        "language_confirmed": language_confirmed,
        "room_joined": room_joined,
        "faq_confirmed": faq_confirmed,
        "userlist_confirmed": userlist_confirmed,
    }
    raise TimeoutError(
        f"Japanese dictionary smoke did not satisfy all conditions: {missing}\n"
        f"Recent protocol:\n{excerpt}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    asyncio.run(run_smoke(args.port, args.timeout, args.output))


if __name__ == "__main__":
    main()
