#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import secrets
import time

import websockets


def to_id(value: str) -> str:
    return "".join(character.lower() for character in value if character.isalnum())


def protocol_lines(message: str) -> list[str]:
    return [line for line in message.splitlines() if line.startswith("|")]


async def wait_for_named_login(websocket, probe_name: str, deadline: float) -> None:
    await websocket.send(f"|/trn {probe_name},0,")
    while time.monotonic() < deadline:
        message = await asyncio.wait_for(websocket.recv(), timeout=max(0.1, deadline - time.monotonic()))
        for line in protocol_lines(message):
            parts = line.split("|")
            if len(parts) >= 4 and parts[1] == "updateuser" and to_id(parts[2]) == to_id(probe_name):
                if parts[3] == "1":
                    return
                raise RuntimeError(f"health probe could not claim its local name: {line}")
    raise TimeoutError("timed out while naming the health probe")


async def query_user(websocket, username: str, deadline: float) -> dict | None:
    await websocket.send(f"|/cmd userdetails {username}")
    while time.monotonic() < deadline:
        message = await asyncio.wait_for(websocket.recv(), timeout=max(0.1, deadline - time.monotonic()))
        for line in protocol_lines(message):
            prefix = "|queryresponse|userdetails|"
            if not line.startswith(prefix):
                continue
            data = json.loads(line[len(prefix):])
            if to_id(str(data.get("userid", ""))) == to_id(username):
                return data
    return None


async def check(username: str, port: int, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    uri = f"ws://127.0.0.1:{port}/showdown/websocket"
    probe_name = f"HealthProbe{secrets.token_hex(3)}"[:18]

    async with websockets.connect(uri) as websocket:
        while time.monotonic() < deadline:
            message = await asyncio.wait_for(websocket.recv(), timeout=max(0.1, deadline - time.monotonic()))
            if any(line.startswith("|challstr|") for line in protocol_lines(message)):
                break
        else:
            raise TimeoutError("Showdown did not send a challenge string")

        await wait_for_named_login(websocket, probe_name, deadline)

        while time.monotonic() < deadline:
            details = await query_user(websocket, username, deadline)
            if details and details.get("rooms") is not False:
                print(f"Showdown user {details.get('name', username)} is online.")
                return
            await asyncio.sleep(0.5)

    raise TimeoutError(f"Showdown user {username} did not become online")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("username")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--timeout", type=float, default=30)
    args = parser.parse_args()
    asyncio.run(check(args.username, args.port, args.timeout))


if __name__ == "__main__":
    main()
