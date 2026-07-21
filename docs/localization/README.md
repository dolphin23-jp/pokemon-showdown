# Japanese localization operations

この文書は、個人用 Pokémon Showdown + foul-play 環境における日本語化の運用正本です。現在の構成、翻訳責任範囲、検証、障害対応、ロールバックをまとめます。

## 現在の状態

Phase 1 T1-12 時点では、次の状態です。

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
- foul-play受信データとRust `poke-engine`入力に日本語名を混入させない
- Rust境界で`pikachu`、`thunderbolt`、`static`、`lightball`を維持する

作業記録:

- [T1-07 表示名API](./phase-1-t1-07-display-name-api.md)
- [T1-08 生成名称表](./phase-1-t1-08-generated-name-maps.md)
- [T1-09 対戦選択UI](./phase-1-t1-09-battle-controls.md)
- [T1-10 サーバープロトコル不変テスト](./phase-1-t1-10-protocol-invariants.md)
- [T1-11 foul-play受信ログ不変テスト](./phase-1-t1-11-foul-play-input-invariants.md)
- [T1-12 Rust AI境界のIDテスト](./phase-1-t1-12-poke-engine-id-invariants.md)

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
```

主なファイル:

| 役割 | ファイル |
| --- | --- |
| Render定義 | `render.yaml` |
| Docker構築 | `Dockerfile` |
| Render統合smoke | `.github/workflows/render-smoke.yml` |
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

## 翻訳責任範囲

### サーバー辞書

`translations/japanese/`はユーザーごとの言語設定に基づくコマンド応答やサーバー表示文を担当します。

順序:

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

`scripts/patch-foul-play-raw-receive-log.py`は、固定foul-playの`PSWebsocketClient.receive_message()`へテスト専用の記録処理を追加します。

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

### opt-in境界記録

`scripts/patch-foul-play-poke-engine-boundary-log.py`は、固定foul-playの`get_result_from_mcts(...)`へ監査を追加します。

```text
FOUL_PLAY_POKE_ENGINE_BOUNDARY_LOG=/app/.runtime/poke-engine-boundary.jsonl
```

監査点は次です。

```text
serialized state
  -> PokeEngineState.from_string(state)
  -> [T1-12 audit]
  -> monte_carlo_tree_search(poke_engine_state, ...)
```

記録対象:

- `serialized_state`
- Rust-backed `State.to_string()`の`rust_state`
- `side_one`・`side_two`のPokemon IDs
- ability IDs
- base ability IDs
- item IDs
- move IDs

`serialized_state == rust_state`を完全一致で要求します。

### 決定論的単体テスト

`scripts/test-foul-play-poke-engine-boundary-log.py`は固定状態で次を確認します。

```text
pikachu
thunderbolt
static
lightball
```

環境変数なしでは境界ログを作成・追記しません。

### 実戦smoke

`config/bss-engine-boundary-bot.txt`の先頭個体は次です。

```text
Pikachu @ Light Ball
Ability: Static
- Thunderbolt
```

`scripts/smoke-bss-poke-engine-boundary-invariants.py`は`EngineBoundaryBot`へ実際にchallengeし、team preview MCTSで生成されたRust-backed Stateを検査します。

完了条件:

- `pikachu`をspecies IDとして取得
- `thunderbolt`をmove IDとして取得
- `static`をability IDとして取得
- `lightball`をitem IDとして取得
- 4値が同じPokemonのRust snapshotに存在
- `serialized_state`と`rust_state`が完全一致
- `Pikachu`、`Thunderbolt`、`Static`、`Light Ball`がRust入力にない
- 日本語文字がRust入力にない

専用artifact:

```text
bss-poke-engine-boundary-invariant-diagnostics
```

T1-12は専用コンテナで実行し、完了後に削除します。T1-11、T1-10、通常BSS、post-faint回帰は従来の別コンテナで実行します。

## 絶対に変えない境界

以下は日本語化しません。

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
- Rust `poke-engine`へ渡すID

表示名API、サーバー辞書、raw audit、Rust boundary auditは互いに独立させます。監査ログは翻訳元、逆変換元、状態修正には使用しません。

## 固定リビジョン

```text
client: 80c72741b52e91d35ee778982a936ea42526c078
client upstream base: 085dfabd9bc53c730ac459edf5c28088677adfc2
foul-play: 25c976f05cbf2880eaa579afd6db1dcb2c3b57c6
display source: 227b573712414a86ba299d322fa398fbb2893edc
```

T1-12はクライアントSHAを変更しません。

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
```

追加検証:

```bash
node scripts/test-launcher-japanese-language.js
node scripts/test-launcher-pinned-client.js
python3 scripts/check-pinned-client.py --verify-remote
python3 scripts/check-localization-docs.py
python3 scripts/check-phase1-baseline.py
```

Render smokeはDocker build、固定クライアント検証、T1-10複製入力、T1-12専用境界コンテナ、T1-11、T1-10実サーバー、通常BSS、post-faint、access gate、固定クライアント配信、iPad画面取得を連続して実行します。

## 障害対応

### T1-12境界ログが作成されない

1. 専用コンテナに`FOUL_PLAY_POKE_ENGINE_BOUNDARY_LOG`が設定されているか確認
2. `scripts/patch-foul-play-poke-engine-boundary-log.py`がDocker buildで適用されたか確認
3. `scripts/test-foul-play-poke-engine-boundary-log.py`を実行
4. `EngineBoundaryBot`がnamed login済みか確認
5. team preview MCTSが開始されたか確認
6. `poke-engine-boundary-container.log`を確認

### target IDが不足する

1. `config/bss-engine-boundary-bot.txt`の先頭がPikachuか確認
2. Light Ball、Static、Thunderboltの綴りを変更していないか確認
3. `poke-engine-boundary.jsonl`の`side_one`と`side_two`を確認
4. `serialized_state`と`rust_state`が一致するか確認
5. fallbackでMCTSが完全に回避されていないか確認

### 日本語混入を検出する

1. T1-10、T1-11、T1-12のartifactを比較
2. 表示名APIがprotocolまたはfoul-play状態へ使用されていないか確認
3. server dictionaryがbattle protocolを置換していないか確認
4. 日本語名から英語IDへの逆変換を追加していないか確認
5. IDや状態を変更せず、表示側の誤接続を修正

## ロールバック

T1-12は表示機能、protocol、クライアントSHA、Rust入力を変更しません。

境界監査に問題がある場合:

1. T1-12のserver squash mergeをrevertするPRを作る
2. T1-11時点のruntime動作を維持する
3. ID、protocol、表示機能、foul-play状態を変えてテストを回避しない
4. patch適用点、JSONL書き込み、State round-trip、専用コンテナを先に修正する

## 変更レビューのチェックリスト

- [ ] `data/`と`sim/`に変更がない
- [ ] クライアントSHAを変更していない
- [ ] T1-11 raw記録はopt-inのまま
- [ ] T1-12境界記録は`FOUL_PLAY_POKE_ENGINE_BOUNDARY_LOG`設定時のみ有効
- [ ] 監査点は`from_string()`後・MCTS前
- [ ] `serialized_state == rust_state`
- [ ] `pikachu`、`thunderbolt`、`static`、`lightball`を同一個体で確認
- [ ] Rust境界に表示名・日本語文字がない
- [ ] `/choose`・`/team`・Import/Exportを変更していない
- [ ] T1-10とT1-11が継続成功
- [ ] foul-play通常対戦とpost-faint回復が成功
- [ ] Node.js CI、文書CI、Render smokeが成功
- [ ] access gateとiPad画面取得が成功

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
