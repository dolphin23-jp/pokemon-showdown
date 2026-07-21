#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import pathlib
import tempfile
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
TARGET = ROOT / "foul-play" / "fp" / "websocket_client.py"


class FakeWebsocket:
    def __init__(self, messages: list[str]):
        self.messages = iter(messages)

    async def recv(self) -> str:
        return next(self.messages)


def load_module():
    spec = importlib.util.spec_from_file_location("patched_foul_play_websocket_client", TARGET)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Could not import patched foul-play module: {TARGET}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    source = TARGET.read_text(encoding="utf-8")
    required_markers = [
        "PERSONAL_SERVER_RAW_RECEIVE_LOG",
        'os.environ.get("FOUL_PLAY_RAW_RECEIVE_LOG")',
        '"received_at_ns": time.time_ns()',
        '"message": message',
        "ensure_ascii=False",
    ]
    missing = [marker for marker in required_markers if marker not in source]
    if missing:
        raise AssertionError(f"Raw receive instrumentation markers are missing: {missing}")

    module = load_module()
    raw_message = (
        ">battle-foul-play-input-invariant\n"
        "|request|{\"active\":[{\"moves\":[{\"move\":\"Astral Barrage\","
        "\"id\":\"astralbarrage\"}]}],\"side\":{\"pokemon\":[{\"ident\":"
        "\"p2: Calyrex-Shadow\",\"details\":\"Calyrex-Shadow, L50\","
        "\"baseAbility\":\"asonespectrier\",\"item\":\"choicespecs\","
        "\"moves\":[\"astralbarrage\"]}]}}"
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        log_path = pathlib.Path(temp_dir) / "received.jsonl"
        client = module.PSWebsocketClient()
        client.websocket = FakeWebsocket([raw_message, "unrecorded"])

        with mock.patch.dict(
            os.environ,
            {"FOUL_PLAY_RAW_RECEIVE_LOG": str(log_path)},
            clear=False,
        ):
            received = asyncio.run(client.receive_message())

        if received != raw_message:
            raise AssertionError("receive_message changed the inbound WebSocket frame")

        records = [
            json.loads(line)
            for line in log_path.read_text(encoding="utf-8").splitlines()
            if line
        ]
        if len(records) != 1:
            raise AssertionError(f"Expected one raw receive record, found {len(records)}")
        if records[0]["message"] != raw_message:
            raise AssertionError("The JSONL record did not preserve the exact inbound frame")
        if not isinstance(records[0]["received_at_ns"], int):
            raise AssertionError("The raw receive record is missing its integer timestamp")

        with mock.patch.dict(os.environ, {}, clear=True):
            received_without_log = asyncio.run(client.receive_message())
        if received_without_log != "unrecorded":
            raise AssertionError("Opt-out receive_message changed the inbound frame")
        if len(log_path.read_text(encoding="utf-8").splitlines()) != 1:
            raise AssertionError("Raw receive logging was not disabled when the environment variable was absent")

    print(
        json.dumps(
            {
                "task": "Phase 1 T1-11",
                "exact_frame_preserved": True,
                "jsonl_recording_opt_in": True,
                "default_runtime_unchanged": True,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
