# Japanese localization operations

この文書は、個人用 Pokémon Showdown + foul-play 環境における日本語化の運用正本です。現在の構成、翻訳責任範囲、検証、障害対応、ロールバック、Phase 1完了条件をまとめます。

## 現在の状態

Phase 1 T1-13では、T1-00からT1-12までのruntimeを変更せず、最終統合回帰を実施します。

- ブラウザの既定入口は `/client.html`
- クライアントは `dolphin23-jp/pokemon-showdown-client` の完全SHAからDocker内でビルドされる
- 固定情報は `config/pokemon-showdown-client.json` に保存される
- 完成したクライアントは `/opt/pokemon-showdown-client` に格納される
- 実行時に `play.pokemonshowdown.com` からHTML・JavaScript・CSSを取得しない
- ブラウザは同一オリジンの `/showdown` を通じてローカルサーバーへ接続する
- namedログイン後に一度だけ `/updatesettings {"language":"japanese"}` を送る
- `window.PSDisplayNames` が表示専用APIを提供する
- `window.BattleJapaneseDisplayNames` がspecies・moves・abilities・itemsの生成済み日本語名を保持する
- 技選択、交代、選出、味方・対象選択ボタンの見える文字だけを日本語化する
- `data-cmd`、`data-tooltip`、request JSON、正規化ID、battle protocolはcanonical Englishのまま
- T1-10がサーバー側の`|request|`・`|switch|`・`|move|`・`/choose`・`/team`を検証する
- T1-11がfoul-playの`websocket.recv()`直後の生フレームを実戦で検査する
- T1-12が`PokeEngineState.from_string(state)`後・`monte_carlo_tree_search(...)`前のRust境界を検査する
- T1-13が3つの前提CIを同一head SHAで待ち、Render smokeの成果物を統合監査する
- 最終レポートの`ready_for_phase2`は全条件成功時だけ`true`になる

作業記録:

- [T1-07 表示名API](./phase-1-t1-07-display-name-api.md)
- [T1-08 生成名称表](./phase-1-t1-08-generated-name-maps.md)
- [T1-09 対戦選択UI](./phase-1-t1-09-battle-controls.md)
- [T1-10 サーバープロトコル不変テスト](./phase-1-t1-10-protocol-invariants.md)
- [T1-11 foul-play受信ログ不変テスト](./phase-1-t1-11-foul-play-input-invariants.md)
- [T1-12 Rust AI境界のIDテスト](./phase-1-t1-12-poke-engine-id-invariants.md)
- [T1-13 Phase 1統合回帰](./phase-1-t1-13-integration-regression.md)

## 構成

```text
Browser
  -> launcher : $PORT / $LAUNCHER_PORT
       -> /client.html
          /opt/pokemon-showdown-client
          -> battle-display-names.js
             -> window.BattleJapaneseDisplayNames
             -> window.PSDisplayNames
             -> visible battle control text only
       -> /showdown
          Pokemon Showdown server : $SHOWDOWN_PORT
          -> raw |request|, |switch|, |move| remain canonical English

foul-play
  -> PSWebsocketClient.receive_message()
     -> exact frame returned unchanged
     -> optional JSONL audit only when FOUL_PLAY_RAW_RECEIVE_LOG is set
  -> canonical English battle state
  -> battle_to_poke_engine_state(...)
  -> State.to_string()
  -> child process
  -> PokeEngineState.from_string(state)
     -> optional JSONL audit only when FOUL_PLAY_POKE_ENGINE_BOUNDARY_LOG is set
  -> monte_carlo_tree_search(poke_engine_state, ...)
  -> Rust poke-engine

Render smoke test
  -> Docker clean build and all runtime/browser evidence
  -> GitHub Actions artifacts

Phase 1 integration regression
  -> scripts/wait-phase1-workflows.py
  -> same-SHA documentation / Node.js / Render smoke success
  -> download successful Render smoke artifacts
  -> scripts/audit-phase1-integration.py
  -> phase1-integration-regression-report
```

主なファイル:

| 役割 | ファイル |
| --- | --- |
| Render定義 | `render.yaml` |
| Docker構築 | `Dockerfile` |
| Render証拠生成 | `.github/workflows/render-smoke.yml` |
| T1-13最終判定 | `.github/workflows/phase1-integration-regression.yml` |
| ランチャー | `scripts/launcher-server.js` |
| 固定クライアント配信 | `scripts/pinned-client-preload.js` |
| クライアント固定情報 | `config/pokemon-showdown-client.json` |
| T1-10複製入力テスト | `scripts/test-japanese-protocol-invariants.js` |
| T1-10実サーバーsmoke | `scripts/smoke-bss-protocol-invariants.py` |
| T1-11受信記録パッチ | `scripts/patch-foul-play-raw-receive-log.py` |
| T1-11受信記録単体テスト | `scripts/test-foul-play-raw-receive-log.py` |
| T1-11実戦smoke | `scripts/smoke-bss-foul-play-input-invariants.py` |
| T1-12境界記録パッチ | `scripts/patch-foul-play-poke-engine-boundary-log.py` |
| T1-12境界記録単体テスト | `scripts/test-foul-play-poke-engine-boundary-log.py` |
| T1-12実戦smoke | `scripts/smoke-bss-poke-engine-boundary-invariants.py` |
| T1-12専用Botチーム | `config/bss-engine-boundary-bot.txt` |
| Phase 1基準検証 | `scripts/check-phase1-baseline.py` |
| 文書・契約検証 | `scripts/check-localization-docs.py` |
| T1-13 CI待ち合わせ | `scripts/wait-phase1-workflows.py` |
| T1-13成果物監査 | `scripts/audit-phase1-integration.py` |

## 翻訳責任範囲

### サーバー辞書

`translations/japanese/`はユーザーごとの言語設定に基づくコマンド応答やサーバー表示文を担当します。

1. `/trn <name>,0,`
2. named状態を確認
3. `/updatesettings {"language":"japanese"}`を一度送信

サーバー辞書はbattle protocolの名前・IDを翻訳しません。

### クライアント表示名API

固定クライアントは次を公開します。

- `displaySpeciesName(...)`
- `displayMoveName(...)`
- `displayAbilityName(...)`
- `displayItemName(...)`

未登録時はcanonical EnglishのDex名へフォールバックします。Dexオブジェクト、入力値、ID、保存データ、通信データは変更しません。

### 生成名称表

生成元:

- repository: `PokeAPI/pokeapi`
- commit: `227b573712414a86ba299d322fa398fbb2893edc`
- Japanese language ID: `11`

生成対象はspecies、moves、abilities、itemsです。生成値は表示専用であり、日本語表示名から英語IDを逆生成しません。

### 対戦選択UI

`MutationObserver`は`childList`、`subtree`、`characterData`を監視します。変更するのは直下の表示テキストノードだけです。

```text
display_text_only: true
mutates_commands: false
mutates_tooltips: false
preserves_unknown_names: true
```

ニックネームと未知名は元の表示を保持します。

## T1-10 サーバープロトコル不変テスト

`scripts/test-japanese-protocol-invariants.js`は同じcanonical English入力を、生プロトコル保存用と表示用へ複製します。

- `|request|`、`|switch|`、`|move|`は変更なし
- `/choose move 1`、`/switch 1`は変更なし
- tooltipsは変更なし
- `Thunderbolt`の表示だけが`10まんボルト`
- `Pikachu`の表示だけが`ピカチュウ`

`scripts/smoke-bss-protocol-invariants.py`は日本語設定有効下の実サーバーで同じ境界を確認します。

## T1-11 foul-play受信ログ不変テスト

`scripts/patch-foul-play-raw-receive-log.py`は固定foul-playの`PSWebsocketClient.receive_message()`へテスト専用の記録処理を追加します。

```text
FOUL_PLAY_RAW_RECEIVE_LOG=/app/.runtime/foul-play-received.jsonl
```

設定時のみ、`websocket.recv()`が返した文字列をJSONLへ保存します。保存後も同じ`message`をそのまま返します。環境変数がない通常起動ではファイルを開かず、ログを書かず、メッセージやbattle処理を変更しません。

`scripts/smoke-bss-foul-play-input-invariants.py`は当該battle roomのBot側`|request|`・`|switch|`・`|move|`を実戦で取得し、species・moves・abilities・itemsの全カテゴリと日本語混入ゼロを確認します。

専用artifact:

```text
bss-foul-play-input-invariant-diagnostics
```

## T1-12 Rust AI境界のIDテスト

`scripts/patch-foul-play-poke-engine-boundary-log.py`は固定foul-playの`get_result_from_mcts(...)`へ監査を追加します。

```text
FOUL_PLAY_POKE_ENGINE_BOUNDARY_LOG=/app/.runtime/poke-engine-boundary.jsonl
```

監査点:

```text
serialized state
  -> PokeEngineState.from_string(state)
  -> [T1-12 audit]
  -> monte_carlo_tree_search(poke_engine_state, ...)
```

実戦smokeは`EngineBoundaryBot`へchallengeし、同一Pokemonで次を確認します。

```text
PIKACHU     -> pikachu
THUNDERBOLT -> thunderbolt
STATIC      -> static
LIGHTBALL   -> lightball
```

- raw Rust enum tokenを変更しない
- `serialized_state == rust_state`
- 日本語文字がない
- 表示文字列をRust入力へ渡さない

専用artifact:

```text
bss-poke-engine-boundary-invariant-diagnostics
```

## T1-13 Phase 1統合回帰

過去計画の完了条件:

```text
Dockerをクリーンビルドして全テスト・ブラウザ確認・成果物監査
全条件成功
Phase 2へ進める最終報告を作成
```

### 証拠生成

`Render smoke test`は既存の経路を変更せず、次を実行します。

1. T1-13 baselineと固定クライアントremote検証
2. Docker clean build
3. 埋め込みclient manifestとT1-10複製入力fixture
4. T1-12専用Rust境界コンテナ
5. T1-11 foul-play受信実戦
6. T1-10サーバープロトコル実戦
7. 通常BSS turn 1
8. post-faint強制交代
9. access gateと固定クライアント配信
10. 外部Showdown clientを遮断したブラウザ確認
11. 1024×1366のlauncher/client PNG
12. 証拠artifactのアップロード

### 同一SHAのCI待ち合わせ

`scripts/wait-phase1-workflows.py`は、PRのhead SHAに対する以下3 workflowをGitHub Actions APIで待ちます。

- `Localization documentation`
- `Node.js CI`
- `Render smoke test`

いずれかが失敗した場合はT1-13も失敗します。すべて成功した場合、成功したRender smokeのrun IDを`phase1-workflow-runs.json`へ固定します。

### 成果物監査

`.github/workflows/phase1-integration-regression.yml`は固定したrun IDのartifactだけをダウンロードし、`merge-multiple: true`で一つのディレクトリへ展開します。

`scripts/audit-phase1-integration.py`は次のstatusがすべて`0`であることを要求します。

- `docker-build.status`
- `bss-poke-engine-boundary-invariants.status`
- `bss-foul-play-input-invariants.status`
- `bss-protocol-invariants.status`
- `bss-smoke.status`
- `bss-faint-smoke.status`

さらに次を検証します。

- T1-13 baselineで`data/`と`sim/`の変更がない
- client pinが`80c72741b52e91d35ee778982a936ea42526c078`
- remote pinと埋め込みclient manifestが一致
- T1-10/T1-11/T1-12の機械可読レポートが成功
- access gate、same-origin `/showdown`、日本語bootstrapが維持
- PNG signature、IHDR、1024×1366
- 必須成果物すべてのbyte sizeとSHA-256

HTTP statusで404を検証済みの`client-traversal.txt`だけは空本文を許容し、空の場合もSHA-256を記録します。

最終ファイル:

```text
/tmp/phase1-integration-regression.json
```

専用artifact:

```text
phase1-integration-regression-report
```

成功時の必須値:

```json
{
  "phase": "Phase 1",
  "task": "T1-13",
  "phase1_complete": true,
  "ready_for_phase2": true
}
```

`ready_for_phase2`は3つの前提CIと全成果物条件が成功した場合だけ`true`になります。

## 絶対に変えない境界

以下は日本語化・監査のために変更しません。

- `data/`
- `sim/`
- species ID
- move ID
- ability ID
- item ID
- WebSocket battle protocol
- `|request|`
- `|switch|`
- `|move|`
- `/choose`
- `/team`
- Team Import/Export
- challenge format ID
- foul-playへ渡す名前・ID・状態
- Rust `poke-engine`へ渡すIDとState

## 固定リビジョン

```text
client: 80c72741b52e91d35ee778982a936ea42526c078
client upstream base: 085dfabd9bc53c730ac459edf5c28088677adfc2
foul-play: 25c976f05cbf2880eaa579afd6db1dcb2c3b57c6
display source: 227b573712414a86ba299d322fa398fbb2893edc
```

T1-13はクライアントSHAを変更しません。

## 必須テスト

```bash
node scripts/test-japanese-protocol-invariants.js \
  --client-root /opt/pokemon-showdown-client

.venv/bin/python scripts/test-foul-play-local-login.py
.venv/bin/python scripts/test-foul-play-battle-fallbacks.py
.venv/bin/python scripts/test-foul-play-raw-receive-log.py
.venv/bin/python scripts/test-foul-play-poke-engine-boundary-log.py

.venv/bin/python scripts/smoke-bss-poke-engine-boundary-invariants.py \
  --bot EngineBoundaryBot --port 8000 --timeout 120 \
  --boundary-log /app/.runtime/poke-engine-boundary.jsonl

.venv/bin/python scripts/smoke-bss-foul-play-input-invariants.py \
  --bot FoulPlayAI --port 8000 --timeout 90 \
  --raw-log /app/.runtime/foul-play-received.jsonl

.venv/bin/python scripts/smoke-bss-protocol-invariants.py \
  --bot FoulPlayAI --port 8000 --timeout 90

.venv/bin/python scripts/smoke-bss-battle.py \
  --bot FoulPlayAI --port 8000 --timeout 90

.venv/bin/python scripts/smoke-bss-faint-recovery.py \
  --bot FoulPlayAI --port 8000 --timeout 150

python3 scripts/audit-phase1-integration.py \
  --artifact-root /tmp/phase1-artifacts \
  --output /tmp/phase1-integration-regression.json
```

追加検証:

```bash
node scripts/test-launcher-japanese-language.js
node scripts/test-launcher-pinned-client.js
python3 scripts/check-pinned-client.py --verify-remote
python3 scripts/check-localization-docs.py
python3 scripts/check-phase1-baseline.py
```

## 障害対応

### 最終監査が失敗する

1. `phase1-integration-regression.json`を成功扱いに手修正しない
2. `phase1-workflow-runs.json`で対象SHAとrun IDを確認する
3. 非0の`.status`を特定する
4. 欠落または空の成果物を特定する
5. JSON reportのtaskとverified値を確認する
6. PNGのwidth/heightを確認する
7. 元テストまたは成果物生成を修正する
8. Docker clean buildから全回帰を再実行する

### 日本語混入を検出する

1. T1-10、T1-11、T1-12のartifactを比較
2. 表示名APIがprotocolまたはfoul-play状態へ使用されていないか確認
3. server dictionaryがbattle protocolを置換していないか確認
4. 日本語名から英語IDへの逆変換を追加していないか確認
5. IDや状態を変更せず、表示側の誤接続を修正

## ロールバック

T1-13はruntime機能を変更しません。

統合監査に問題がある場合:

1. T1-13のserver squash mergeをrevertするPRを作る
2. T1-12時点のruntime動作を維持する
3. statusや最終reportを偽装してテストを回避しない
4. workflow待ち合わせ、audit対象、成果物取得を修正する

## 変更レビューのチェックリスト

- [ ] `data/`と`sim/`に変更がない
- [ ] クライアントSHAを変更していない
- [ ] T1-10、T1-11、T1-12が継続成功
- [ ] foul-play通常対戦とpost-faint回復が成功
- [ ] access gateと固定クライアント配信が成功
- [ ] 外部Showdown clientなしでbrowser表示できる
- [ ] launcher/client PNGが1024×1366
- [ ] 全6 statusが0
- [ ] 必須成果物のSHA-256 manifestが生成される
- [ ] Localization documentation、Node.js CI、Render smokeが同一SHAで成功
- [ ] Phase 1 integration regressionが成功
- [ ] `phase1_complete: true`
- [ ] `ready_for_phase2: true`

## Phase 1の到達点

- T1-00: 基準状態の固定
- T1-01: 日本語言語設定の自動化
- T1-02: クライアントのフォークと固定
- T1-03: 固定クライアントのDockerビルド
- T1-04: ローカル静的配信経路の追加
- T1-05: 自前クライアントへ完全切替
- T1-06: 翻訳責任範囲の文書化
- T1-07: 表示名APIの骨格
- T1-08: 名称辞書ジェネレーターと生成名称表
- T1-09: 対戦操作UIへの表示名接続
- T1-10: サーバープロトコル不変テスト
- T1-11: foul-play受信ログ不変テスト
- T1-12: Rust AI境界のIDテスト
- T1-13: Phase 1統合回帰

## Phase 1完了

Localization documentation、Node.js CI、Render smoke test、Phase 1 integration regressionがすべて成功し、`phase1-integration-regression-report`内の`ready_for_phase2`が`true`になった時点でPhase 1完了です。

Phase 2の具体的タスクは別の計画で定義します。T1-13の完了だけを根拠に、未定義のPhase 2作業を推測して開始しません。
