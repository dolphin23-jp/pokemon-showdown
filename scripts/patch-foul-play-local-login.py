#!/usr/bin/env python3
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
TARGET = ROOT / "foul-play" / "fp" / "websocket_client.py"
MARKER = "PERSONAL_SERVER_LOCAL_GUEST_LOGIN"
NEEDLE = """        guest_login = self.password is None

        if guest_login:
"""
REPLACEMENT = """        guest_login = self.password is None

        # PERSONAL_SERVER_LOCAL_GUEST_LOGIN
        # This private server runs on loopback with noguestsecurity enabled.
        # Sending /trn directly avoids the public Showdown assertion service,
        # which rejects guest use of names registered on the public server.
        local_guest_login = guest_login and self.address.startswith(
            (\"ws://127.0.0.1:\", \"ws://localhost:\", \"ws://[::1]:\")
        )
        if local_guest_login:
            logger.info(\"Using passwordless login for a trusted local Showdown server\")
            await self.send_message(\"\", [\"/trn \" + self.username + \",0,\"])
            await asyncio.sleep(1)
            return self.username

        if guest_login:
"""


def main() -> None:
    if not TARGET.is_file():
        raise SystemExit(f"foul-play websocket client was not found: {TARGET}")

    source = TARGET.read_text(encoding="utf-8")
    if MARKER in source:
        print("foul-play local-login patch is already applied.")
        return
    if source.count(NEEDLE) != 1:
        raise SystemExit(
            "The pinned foul-play login implementation changed; refusing to apply an unsafe patch."
        )

    TARGET.write_text(source.replace(NEEDLE, REPLACEMENT), encoding="utf-8")
    print("Applied foul-play local-login patch.")


if __name__ == "__main__":
    main()
