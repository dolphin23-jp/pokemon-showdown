#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import pathlib
import sys
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "foul-play"))

from fp.battle.state import Battle, Pokemon  # noqa: E402
from fp.config import FoulPlayConfig  # noqa: E402
from fp.modes.base import async_pick_move  # noqa: E402
from fp.modes.bss import BSSMode  # noqa: E402

FoulPlayConfig.pokemon_format = "gen9nationaldexallgenerationsbss"
FoulPlayConfig.team_preview_search_parallelism = 1
FoulPlayConfig.team_preview_search_time_ms = 1
FoulPlayConfig.search_threads = 1


class FakeWebSocketClient:
    def __init__(self) -> None:
        self.messages: list[tuple[str, list[str]]] = []

    async def send_message(self, room: str, message: list[str]) -> None:
        self.messages.append((room, message))


def make_pokemon(names: list[str]) -> list[Pokemon]:
    team = []
    for index, name in enumerate(names, 1):
        # Pass explicit EVs so this focused unit test does not depend on the
        # process-wide random-battle generation defaults being configured.
        pokemon = Pokemon(name, 50, evs=(0, 0, 0, 0, 0, 0))
        pokemon.index = index
        team.append(pokemon)
    return team


async def test_bss_preview_fallback() -> None:
    battle = Battle("battle-fallback-test")
    battle.rqid = 17
    battle.mode = BSSMode()
    battle.user.reserve = make_pokemon(
        ["gholdengo", "tyranitar", "clodsire", "alomomola", "landorustherian", "volcarona"]
    )
    battle.opponent.reserve = make_pokemon(
        ["torterra", "blastoisemega", "torkoal", "drednaw", "carracosta", "sableye"]
    )
    websocket = FakeWebSocketClient()

    with mock.patch(
        "fp.modes.bss.bss_team_preview",
        side_effect=RuntimeError("simulated incomplete inference data"),
    ):
        await battle.mode.handle_team_preview(battle, websocket)

    assert websocket.messages == [
        ("battle-fallback-test", ["/team 123456|17"])
    ], websocket.messages
    assert [pokemon.name for pokemon in battle.user.reserve[:3]] == [
        "gholdengo",
        "tyranitar",
        "clodsire",
    ]
    assert [pokemon.name for pokemon in battle.user.reserve[3:]] == ["none", "none", "none"]
    assert all(
        battle.opponent_team_preview_affinities[pokemon.name] == 1.0
        for pokemon in battle.opponent.reserve
    )


async def test_move_search_fallback() -> None:
    battle = Battle("battle-move-fallback-test")
    battle.rqid = 23
    battle.team_preview = True
    battle.request_json = {
        "active": [
            {
                "moves": [
                    {"id": "recover", "pp": 0, "disabled": True},
                    {"id": "shadowball", "pp": 24, "disabled": False},
                ]
            }
        ],
        "side": {"pokemon": []},
    }

    with mock.patch(
        "fp.modes.base.find_best_move",
        side_effect=RuntimeError("simulated engine serialization failure"),
    ):
        decision = await async_pick_move(battle)

    assert decision == ["/choose move 2", "23"], decision


async def test_forced_switch_skips_search() -> None:
    battle = Battle("battle-forced-switch-test")
    battle.rqid = 31
    battle.team_preview = True
    battle.force_switch = True
    battle.request_json = {
        "forceSwitch": [True],
        "side": {
            "pokemon": [
                {"active": True, "condition": "0 fnt"},
                {"active": False, "condition": "175/175"},
                {"active": False, "condition": "200/200"},
            ]
        },
    }

    with mock.patch(
        "fp.modes.base.find_best_move",
        side_effect=AssertionError("forced switches must not launch MCTS"),
    ):
        decision = await async_pick_move(battle)

    assert decision == ["/switch 2", "31"], decision


async def test_decision_formatting_fallback() -> None:
    battle = Battle("battle-format-fallback-test")
    battle.rqid = 37
    battle.team_preview = True
    battle.user.active = make_pokemon(["gengar"])[0]
    battle.request_json = {
        "active": [
            {
                "moves": [
                    {"id": "shadowball", "pp": 24, "disabled": False},
                ]
            }
        ],
        "side": {"pokemon": []},
    }

    with (
        mock.patch("fp.modes.base.find_best_move", return_value="shadowball"),
        mock.patch(
            "fp.modes.base.format_decision",
            side_effect=KeyError("simulated National Dex switch/format error"),
        ),
    ):
        decision = await async_pick_move(battle)

    assert decision == ["/choose move 1", "37"], decision


async def main() -> None:
    await test_bss_preview_fallback()
    await test_move_search_fallback()
    await test_forced_switch_skips_search()
    await test_decision_formatting_fallback()
    print("foul-play battle fallback tests passed.")


if __name__ == "__main__":
    asyncio.run(main())
