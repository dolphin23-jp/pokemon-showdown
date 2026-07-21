#!/usr/bin/env python3
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def replace_exact(path: str, old: str, new: str, *, count: int = 1) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    actual = text.count(old)
    if actual != count:
        raise AssertionError(
            f"Expected {count} occurrence(s) in {path}, found {actual}: {old!r}"
        )
    target.write_text(text.replace(old, new), encoding="utf-8")
    print(f"patched {path}: {old!r}")


def main() -> None:
    replace_exact(
        "translations/japanese/main.ts",
        '\t\t"Tiering FAQ": "",',
        '\t\t"Tiering FAQ": "ティア制度に関するよくある質問",',
    )
    replace_exact(
        "translations/japanese/main.ts",
        '\t\t"Badge FAQ": "",',
        '\t\t"Badge FAQ": "バッジに関するよくある質問",',
    )
    replace_exact(
        "translations/japanese/main.ts",
        '\t\t"If you need help, try opening a <a href=\\"view-help-request\\" class=\\"button\\">help ticket</a>": "ヘルプを求めている場合は、<a href=\\"view-help-request\\" class=\\"button\\">help ticket</a>にてリクエストを送信してください。",',
        '\t\t"If you need help, try opening a <a href=\\"view-help-request\\" class=\\"button\\">help ticket</a>": "ヘルプが必要な場合は、<a href=\\"view-help-request\\" class=\\"button\\">ヘルプチケット</a>を作成してください。",',
    )

    replace_exact(
        "translations/japanese/helptickets.ts",
        '\t\t"Please <button name=\\"login\\" class=\\"button\\">Log In</button> to request help.": "Please <button name=\\"login\\" class=\\"button\\">ログイン</button>してヘルプを要請する",',
        '\t\t"Please <button name=\\"login\\" class=\\"button\\">Log In</button> to request help.": "ヘルプを要請するには、<button name=\\"login\\" class=\\"button\\">ログイン</button>してください。",',
    )
    replace_exact(
        "translations/japanese/helptickets.ts",
        "/ignire [username]",
        "/ignore [username]",
        count=2,
    )

    replace_exact(
        "translations/japanese/minor-activities.ts",
        '\t\t"#${number} in queue": "{number}番目",',
        '\t\t"#${number} in queue": "キューの${number}番目",',
    )

    replace_exact(
        "translations/japanese/repeats.ts",
        "\t\t'${user.name} set the Room FAQ \"${topic}\" to be repeated every ${interval} minute(s).': '${user.name}がRoom FAQの \"${topic}\"のリピートを${interval}分間隔で設定しました。',",
        "\t\t'${user.name} set the Room FAQ \"${topic}\" to be repeated every ${interval} minute(s).': '${user.name}がルームFAQ「${topic}」を${interval}分間隔で繰り返すよう設定しました。',",
    )
    replace_exact(
        "translations/japanese/repeats.ts",
        "\t\t'${user.name} set the Room FAQ \"${topic}\" to be repeated every ${interval} chat message(s).': '${user.name}がRoom FAQの \"${topic}\"のリピートをメッセージ数: ${interval}間隔で設定しました。',",
        "\t\t'${user.name} set the Room FAQ \"${topic}\" to be repeated every ${interval} chat message(s).': '${user.name}がルームFAQ「${topic}」を${interval}件のチャットメッセージごとに繰り返すよう設定しました。',",
    )
    replace_exact(
        "translations/japanese/repeats.ts",
        "\t\t'The text for the Room FAQ \"${topic}\" is already being repeated.': 'Room FAQの \"${topic}\"はすでにリピートされています。',",
        "\t\t'The text for the Room FAQ \"${topic}\" is already being repeated.': 'ルームFAQ「${topic}」はすでに繰り返し表示されています。',",
    )

    replace_exact(
        "server/chat-commands/core.ts",
        '\t\tlet output = `There ${Chat.plural(userList, "are", "is")} <strong style="color:#24678d">${Chat.count(userList, "</strong> users")} in this room:<br />`;',
        '\t\tconst count = userList.length;\n'
        '\t\tlet output = count === 1 ?\n'
        '\t\t\tthis.tr`There is <strong style="color:#24678d">${count}</strong> user in this room:<br />` :\n'
        '\t\t\tthis.tr`There are <strong style="color:#24678d">${count}</strong> users in this room:<br />`;',
    )
    replace_exact(
        "translations/japanese/core-commands.ts",
        '\t\t"Server version: <b>${version}</b>": "サーバーのバージョン: <b>${version}</b>",',
        '\t\t"Server version: <b>${version}</b>": "サーバーのバージョン: <b>${version}</b>",\n'
        '\t\t"There is <strong style=\\"color:#24678d\\">${count}</strong> user in this room:<br />": "この部屋には<strong style=\\"color:#24678d\\">${count}</strong>人のユーザーがいます。<br />",\n'
        '\t\t"There are <strong style=\\"color:#24678d\\">${count}</strong> users in this room:<br />": "この部屋には<strong style=\\"color:#24678d\\">${count}</strong>人のユーザーがいます。<br />",',
    )

    replace_exact(
        "Dockerfile",
        "    && node --check scripts/test-launcher-pinned-client.js \\\n",
        "    && node --check scripts/test-launcher-pinned-client.js \\\n"
        "    && node --check scripts/audit-japanese-server-translations.js \\\n",
    )
    replace_exact(
        "Dockerfile",
        "        scripts/smoke-bss-poke-engine-boundary-invariants.py \\\n",
        "        scripts/smoke-bss-poke-engine-boundary-invariants.py \\\n"
        "        scripts/smoke-japanese-server-dictionary.py \\\n",
    )
    replace_exact(
        "Dockerfile",
        "    && python3 scripts/check-localization-docs.py \\\n",
        "    && python3 scripts/check-localization-docs.py \\\n"
        "    && node scripts/audit-japanese-server-translations.js --check-fixed \\\n"
        "        --json-output /tmp/phase2-japanese-translation-audit.json \\\n",
    )

    workflow = """      - name: Verify bot identity
        run: |
          docker exec showdown-ai \\
            .venv/bin/python scripts/check-showdown-user.py FoulPlayAI --port 8000 --timeout 30
"""
    workflow_with_phase2 = workflow + """      - name: Exercise Phase 2 Japanese server dictionary
        shell: bash
        run: |
          set +e
          docker exec showdown-ai \\
            .venv/bin/python scripts/smoke-japanese-server-dictionary.py \\
              --port 8000 --timeout 60 \\
              --output /app/.runtime/phase2-japanese-server-dictionary.json \\
            > /tmp/phase2-japanese-server-dictionary.log 2>&1
          smoke_status=$?
          echo "$smoke_status" > /tmp/phase2-japanese-server-dictionary.status
          docker cp showdown-ai:/app/.runtime/phase2-japanese-server-dictionary.json \\
            /tmp/phase2-japanese-server-dictionary.json 2>/dev/null || true
          cat /tmp/phase2-japanese-server-dictionary.log
          exit 0
      - name: Upload Phase 2 Japanese dictionary diagnostics
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: phase2-japanese-server-dictionary-diagnostics
          path: |
            /tmp/phase2-japanese-server-dictionary.log
            /tmp/phase2-japanese-server-dictionary.status
            /tmp/phase2-japanese-server-dictionary.json
      - name: Require Phase 2 Japanese server dictionary
        run: test "$(cat /tmp/phase2-japanese-server-dictionary.status)" = 0
"""
    replace_exact(
        ".github/workflows/render-smoke.yml",
        workflow,
        workflow_with_phase2,
    )

    print("Phase 2 server dictionary patches applied successfully.")


if __name__ == "__main__":
    main()
