#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import pathlib
import sys
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "foul-play"))

from fp.websocket_client import PSWebsocketClient  # noqa: E402


class FakeWebSocket:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def recv(self) -> str:
        return "|challstr|1|unused"

    async def send(self, message: str) -> None:
        self.sent.append(message)


async def run_test() -> None:
    websocket = FakeWebSocket()
    client = PSWebsocketClient()
    client.username = "FoulPlayAI"
    client.password = None
    client.address = "ws://127.0.0.1:8000/showdown/websocket"
    client.websocket = websocket
    client.login_uri = "https://play.pokemonshowdown.com/action.php?"

    with mock.patch(
        "fp.websocket_client.requests.post",
        side_effect=AssertionError("public assertion service must not be called"),
    ):
        result = await client.login()

    assert result == "FoulPlayAI", result
    assert websocket.sent == ["|/trn FoulPlayAI,0,"], websocket.sent
    print("Local foul-play login test passed.")


if __name__ == "__main__":
    asyncio.run(run_test())
