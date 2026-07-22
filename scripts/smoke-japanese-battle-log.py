#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import pathlib
import re
import subprocess
import time
from dataclasses import dataclass
from typing import Any

import websockets

ROOT = pathlib.Path(__file__).resolve().parents[1]
FORMAT = "gen9customgame"
ALPHA = "BattleLogAlpha"
BETA = "BattleLogBeta"
JAPANESE_TEXT = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uff66-\uff9f]")

ALPHA_TEAM = """Throh @ Focus Sash
Ability: Guts
Level: 50
EVs: 252 HP / 252 Atk / 4 SpD
Adamant Nature
- Storm Throw
"""

BETA_TEAM = """Smeargle @ Focus Sash
Ability: Own Tempo
Level: 1
EVs: 252 HP / 4 Def / 252 SpD
Relaxed Nature
IVs: 0 Spe
- Nuzzle
"""


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


def pack_team(team: str) -> str:
    result = subprocess.run(
        ["node", "pokemon-showdown", "pack-team"],
        cwd=ROOT,
        input=team,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError(
            f"Could not pack Japanese battle log smoke team: {result.stderr}"
        )
    return result.stdout.strip()


async def wait_for_login(websocket, name: str, deadline: float) -> None:
    sent_name = False
    while time.monotonic() < deadline:
        message = await asyncio.wait_for(
            websocket.recv(), timeout=max(0.1, deadline - time.monotonic())
        )
        for _room, line in protocol_lines(message):
            if line.startswith("|challstr|") and not sent_name:
                sent_name = True
                await websocket.send(f"|/trn {name},0,")
                continue
            fields = line.split("|")
            if (
                len(fields) >= 4
                and fields[1] == "updateuser"
                and to_id(fields[2]) == to_id(name)
            ):
                if fields[3] == "1":
                    return
                raise RuntimeError(f"{name} could not claim its local name: {line}")
    raise TimeoutError(f"{name} could not log in")


@dataclass
class PlayerState:
    name: str
    websocket: Any
    sent_team: bool = False
    sent_move: bool = False


def request_payload(line: str) -> dict[str, Any]:
    return json.loads(line[len("|request|"):])


def is_relevant_protocol(line: str) -> bool:
    ignored = (
        "|request|",
        "|inactive|",
        "|inactiveoff|",
        "|upkeep",
        "|t:",
        "|j|",
        "|J|",
        "|l|",
        "|L|",
        "|c|",
        "|c:|",
    )
    return not line.startswith(ignored)


def require_canonical_protocol(lines: list[str]) -> None:
    for line in lines:
        if JAPANESE_TEXT.search(line):
            raise AssertionError(
                f"Raw battle protocol contains Japanese display text: {line}"
            )


async def run_smoke(
    port: int,
    timeout: float,
    protocol_output: pathlib.Path,
    report_output: pathlib.Path,
) -> None:
    uri = f"ws://127.0.0.1:{port}/showdown/websocket"
    deadline = time.monotonic() + timeout
    alpha_team = pack_team(ALPHA_TEAM)
    beta_team = pack_team(BETA_TEAM)

    async with (
        websockets.connect(uri) as alpha_ws,
        websockets.connect(uri) as beta_ws,
    ):
        await asyncio.gather(
            wait_for_login(alpha_ws, ALPHA, deadline),
            wait_for_login(beta_ws, BETA, deadline),
        )
        await alpha_ws.send(f"|/utm {alpha_team}")
        await beta_ws.send(f"|/utm {beta_team}")
        await alpha_ws.send(f"|/challenge {BETA},{FORMAT}")

        alpha = PlayerState(ALPHA, alpha_ws)
        beta = PlayerState(BETA, beta_ws)
        players = {"alpha": alpha, "beta": beta}
        recv_tasks = {
            asyncio.create_task(alpha_ws.recv()): "alpha",
            asyncio.create_task(beta_ws.recv()): "beta",
        }
        battle_room = ""
        beta_accepted = False
        alpha_protocol: list[str] = []
        observed = {
            "storm_throw": False,
            "super_effective": False,
            "critical_hit": False,
            "nuzzle": False,
            "paralysis": False,
            "turn_two": False,
        }

        while time.monotonic() < deadline:
            remaining = max(0.1, deadline - time.monotonic())
            done, _pending = await asyncio.wait(
                recv_tasks,
                timeout=remaining,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if not done:
                break

            for task in done:
                label = recv_tasks.pop(task)
                player = players[label]
                message = task.result()
                recv_tasks[asyncio.create_task(player.websocket.recv())] = label

                for room, line in protocol_lines(message):
                    if (
                        label == "beta"
                        and line.startswith("|updatechallenges|")
                        and to_id(ALPHA) in to_id(line)
                        and not beta_accepted
                    ):
                        await beta_ws.send(f"|/accept {ALPHA}")
                        beta_accepted = True

                    if room.startswith("battle-"):
                        battle_room = room
                    if not battle_room or room != battle_room:
                        continue

                    if label == "alpha" and is_relevant_protocol(line):
                        alpha_protocol.append(line)

                    if line.startswith("|request|"):
                        request = request_payload(line)
                        rqid = int(request.get("rqid", 0))
                        if request.get("teamPreview") and not player.sent_team:
                            await player.websocket.send(
                                f"{battle_room}|/team 1|{rqid}"
                            )
                            player.sent_team = True
                            continue
                        if (
                            player.sent_team
                            and not player.sent_move
                            and not request.get("wait")
                            and request.get("active")
                        ):
                            await player.websocket.send(
                                f"{battle_room}|/choose move 1|{rqid}"
                            )
                            player.sent_move = True
                        continue

                    if line.startswith("|move|") and "|Storm Throw|" in line:
                        observed["storm_throw"] = True
                    elif line.startswith("|-supereffective|"):
                        observed["super_effective"] = True
                    elif line.startswith("|-crit|"):
                        observed["critical_hit"] = True
                    elif line.startswith("|move|") and "|Nuzzle|" in line:
                        observed["nuzzle"] = True
                    elif line.startswith("|-status|") and line.endswith("|par"):
                        observed["paralysis"] = True
                    elif line == "|turn|2":
                        observed["turn_two"] = True

                if all(observed.values()):
                    await alpha_ws.send(f"{battle_room}|/forfeit")
                    for recv_task in recv_tasks:
                        recv_task.cancel()

                    require_canonical_protocol(alpha_protocol)
                    protocol = "\n".join(alpha_protocol) + "\n"
                    protocol_output.parent.mkdir(parents=True, exist_ok=True)
                    protocol_output.write_text(protocol, encoding="utf-8")

                    report = {
                        "task": "Japanese battle log live turn smoke",
                        "battle_room": battle_room,
                        "format": FORMAT,
                        "players": [ALPHA, BETA],
                        "protocol_line_count": len(alpha_protocol),
                        "protocol_sha256": hashlib.sha256(
                            protocol.encode("utf-8")
                        ).hexdigest(),
                        "observed": observed,
                        "raw_protocol_contains_japanese_display_text": False,
                        "turn_one_completed": observed["turn_two"],
                        "verified": True,
                    }
                    payload = (
                        json.dumps(
                            report,
                            ensure_ascii=False,
                            indent=2,
                            sort_keys=True,
                        )
                        + "\n"
                    )
                    report_output.parent.mkdir(parents=True, exist_ok=True)
                    report_output.write_text(payload, encoding="utf-8")
                    print(payload, end="")
                    return

        for recv_task in recv_tasks:
            recv_task.cancel()
        raise TimeoutError(
            "Japanese battle log smoke did not complete the deterministic first "
            f"turn. Battle room: {battle_room or '(not created)'}; "
            f"observed: {observed}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--timeout", type=float, default=90)
    parser.add_argument(
        "--protocol-output",
        type=pathlib.Path,
        required=True,
    )
    parser.add_argument(
        "--report-output",
        type=pathlib.Path,
        required=True,
    )
    args = parser.parse_args()
    asyncio.run(
        run_smoke(
            args.port,
            args.timeout,
            args.protocol_output,
            args.report_output,
        )
    )


if __name__ == "__main__":
    main()
