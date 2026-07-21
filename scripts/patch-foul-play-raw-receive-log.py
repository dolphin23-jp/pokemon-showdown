#!/usr/bin/env python3
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
TARGET = ROOT / "foul-play" / "fp" / "websocket_client.py"
MARKER = "PERSONAL_SERVER_RAW_RECEIVE_LOG"
IMPORT_NEEDLE = """import json
import time

import logging
"""
IMPORT_REPLACEMENT = """import json
import os
import time

import logging
"""
RECEIVE_NEEDLE = """    async def receive_message(self):
        message = await self.websocket.recv()
        logger.debug("Received message from websocket: {}".format(message))
        return message
"""
RECEIVE_REPLACEMENT = """    async def receive_message(self):
        message = await self.websocket.recv()

        # PERSONAL_SERVER_RAW_RECEIVE_LOG
        # Keep an exact copy of each inbound WebSocket text frame for opt-in
        # integration checks. Normal runtime behavior is unchanged unless the
        # environment variable is set.
        raw_receive_log = os.environ.get("FOUL_PLAY_RAW_RECEIVE_LOG")
        if raw_receive_log:
            with open(raw_receive_log, "a", encoding="utf-8") as stream:
                stream.write(
                    json.dumps(
                        {"received_at_ns": time.time_ns(), "message": message},
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                    + "\n"
                )

        logger.debug("Received message from websocket: {}".format(message))
        return message
"""


def main() -> None:
    if not TARGET.is_file():
        raise SystemExit(f"foul-play websocket client was not found: {TARGET}")

    source = TARGET.read_text(encoding="utf-8")
    if MARKER in source:
        print("foul-play raw receive log patch is already applied.")
        return
    if source.count(IMPORT_NEEDLE) != 1:
        raise SystemExit(
            "The pinned foul-play import block changed; refusing to apply an unsafe patch."
        )
    if source.count(RECEIVE_NEEDLE) != 1:
        raise SystemExit(
            "The pinned foul-play receive_message implementation changed; refusing to apply an unsafe patch."
        )

    source = source.replace(IMPORT_NEEDLE, IMPORT_REPLACEMENT)
    source = source.replace(RECEIVE_NEEDLE, RECEIVE_REPLACEMENT)
    TARGET.write_text(source, encoding="utf-8")
    print("Applied foul-play raw receive log patch.")


if __name__ == "__main__":
    main()
