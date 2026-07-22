#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import re
import secrets
import time
from collections.abc import AsyncIterator

import websockets

ROOM = "lobby"
FAQ_MARKERS = (
    "ティア制度に関するよくある質問",
    "バッジに関するよくある質問",
)
USERLIST_PREFIX = "この部屋には"
ENGLISH_USERLIST = re.compile(r"There (?:is|are) .* users? in this room", re.IGNORECASE)


def to_id(value: str) -> str:
    return "".join(character.lower() for character in value if character.isalnum())


def protocol_lines(message: str) -> AsyncIterator[tuple[str, str]]:
    room = ""
    for line in message.splitlines():
        if line.startswith(">"):
            room = line[1:].strip()
            continue
        if line.startswith("|"):
            yield room, line


def history_excerpt(history: list[str]) -> str:
    if not history:
        return "<no protocol messages received>"
    return "\n---\n".join(history[-20:])


async def receive_message(
    websocket,
    deadline: float,
    history: list[str],
    phase: str,
) -> str:
    try:
        message = await asyncio.wait_for(
            websocket.recv(), timeout=max(0.1, deadline - time.monotonic())
        )
    except TimeoutError as error:
        raise TimeoutError(
            f"Timed out during {phase}. Recent protocol:\n{history_excerpt(history)}"
        ) from error
    if not isinstance(message, str):
        raise TypeError(f"Expected a text WebSocket frame during {phase}")
    history.append(message)
    return message


async def wait_for_challenge_string(
    websocket,
    deadline: float,
    history: list[str],
) -> None:
    while time.monotonic() < deadline:
        message = await receive_message(websocket, deadline, history, "challstr wait")
        if any(line.startswith("|challstr|") for _room, line in protocol_lines(message)):
            return
    raise TimeoutError(
        "Showdown did not send a challenge string. Recent protocol:\n"
        + history_excerpt(history)
    )


async def wait_for_named_login(
    websocket,
    player: str,
    deadline: float,
    history: list[str],
) -> None:
    await websocket.send(f"|/trn {player},0,")
    while time.monotonic() < deadline:
        message = await receive_message(websocket, deadline, history, "named login")
        for _room, line in protocol_lines(message):
            if line.startswith("|nametaken|"):
                raise RuntimeError(f"Smoke user name was rejected: {line}")
            fields = line.split("|")
            if (
                len(fields) >= 4
                and fields[1] == "updateuser"
                and to_id(fields[2]) == to_id(player)
            ):
                if fields[3] == "1":
                    return
                raise RuntimeError(f"Smoke user could not claim its name: {line}")
    raise TimeoutError(
        "Smoke user could not log in. Recent protocol:\n" + history_excerpt(history)
    )


async def run_smoke(port: int, timeout: float, output: pathlib.Path | None) -> None:
    uri = f"ws://127.0.0.1:{port}/showdown/websocket"
    deadline = time.monotonic() + timeout
    player = f"JpDict{secrets.token_hex(5)}"[:18]
    history: list[str] = []
    language_confirmed = False
    room_joined = False
    faq_confirmed = {marker: False for marker in FAQ_MARKERS}
    userlist_confirmed = False
    userlist_responses: list[str] = []

    async with websockets.connect(uri) as websocket:
        await wait_for_challenge_string(websocket, deadline, history)
        await wait_for_named_login(websocket, player, deadline, history)

        # The first /language response is built in the command's original
        # language context. The authoritative confirmation is updateuser.
        await websocket.send("|/language japanese")
        await websocket.send(f"|/join {ROOM}")

        commands_sent = False
        while time.monotonic() < deadline:
            message = await receive_message(
                websocket, deadline, history, "Japanese command verification"
            )

            if '"language":"japanese"' in message:
                language_confirmed = True
            if "|init|chat" in message and "|title|Lobby" in message:
                room_joined = True

            for _room, line in protocol_lines(message):
                if USERLIST_PREFIX in line:
                    userlist_responses.append(line)
                    if ENGLISH_USERLIST.search(line):
                        raise AssertionError(f"/userlist still returned direct English: {line}")
                    if player not in line:
                        raise AssertionError(f"/userlist did not include the logged-in user: {line}")
                    userlist_confirmed = True
                for marker in FAQ_MARKERS:
                    if marker in line:
                        faq_confirmed[marker] = True

            if language_confirmed and room_joined and not commands_sent:
                await websocket.send(f"{ROOM}|/faq tiers")
                await websocket.send(f"{ROOM}|/faq badges")
                await websocket.send(f"{ROOM}|/userlist")
                commands_sent = True

            if language_confirmed and room_joined and userlist_confirmed and all(faq_confirmed.values()):
                report = {
                    "task": "Phase 2 server dictionary live smoke",
                    "player": player,
                    "room": ROOM,
                    "language_command": "/language japanese",
                    "language_setting_confirmed_by_updateuser": True,
                    "commands_checked": ["/faq tiers", "/faq badges", "/userlist"],
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

    missing = {
        "language_confirmed": language_confirmed,
        "room_joined": room_joined,
        "faq_confirmed": faq_confirmed,
        "userlist_confirmed": userlist_confirmed,
    }
    raise TimeoutError(
        f"Japanese dictionary smoke did not satisfy all conditions: {missing}\n"
        f"Recent protocol:\n{history_excerpt(history)}"
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
