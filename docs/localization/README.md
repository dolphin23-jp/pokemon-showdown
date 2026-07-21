# Japanese localization operations

この文書は、個人用 Pokémon Showdown + foul-play 環境における日本語化の運用正本です。現在の構成、翻訳責任範囲、検証、障害対応、ロールバックをまとめます。

## 現在の状態

Phase 1 T1-11 時点では、次の状態です。

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
- foul-play受信データのspecies・moves・abilities・itemsには日本語が混入しない
- Rust `poke-engine`へ渡るID境界はT1-12で別途検証する

作業記録:

- [T1-07 表示名API](./phase-1-t1-07-display-name-api.md)
- [T1-08 生成名称表](./phase-1-t1-08-generated-name-maps.md)
- [T1-09 対戦選択UI](./phase-1-t1-09-battle-controls.md)
- [T1-10 サーバープロトコル不変テスト](./phase-1-t1-10-protocol-invariants.md)
- [T1-11 foul-play受信ログ不変テスト](./phase-1-t1-11-foul-play-input-invariants.md)

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
  -> canonical English request/protocol data
  -> Rust poke-engine boundary

T1-10
  -> duplicated canonical input: raw protocol vs rendered text
  -> live server protocol inspection

T1-11
  -> exact foul-play inbound frame capture
  -> live battle-room scoped inspection
  -> species / moves / abilities / items coverage
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
| 固定クライアント検証 | `scripts/check-pinned-client.py` |
| ビルド済みクライアント検証 | `scripts/check-built-client.py` |
| T1-10複製入力テスト | `scripts/test-japanese-protocol-invariants.js` |
| T1-10実サーバーsmoke | `scripts/smoke-bss-protocol-invariants.py` |
| foul-play受信記録パッチ | `scripts/patch-foul-play-raw-receive-log.py` |
| foul-play受信記録単体テスト | `scripts/test-foul-play-raw-receive-log.py` |
| T1-11実戦smoke | `scripts/smoke-bss-foul-play-input-invariants.py` |
| Phase 1基準検証 | `scripts/check-phase1-baseline.py` |
| 文書・契約検証 | `scripts/check-localization-docs.py` |

## 翻訳責任範囲

### サーバー辞書

`translations/japanese/` は、ユーザーごとの言語設定に基づくコマンド応答やサーバー表示文を担当します。

順序:

1. `/trn <name>,0,`
2. named状態を確認
3. `/updatesettings {"language":"japanese"}` を一度送信

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

生成対象:

- species
- moves
- abilities
- items

生成物:

- `play.pokemonshowdown.com/js/battle-display-names.js`
- `play.pokemonshowdown.com/js/battle-display-names.meta.json`

最低件数:

- species 1000
- moves 800
- abilities 250
- items 1500

生成値は表示専用です。日本語表示名から英語IDを逆生成しません。

### 対戦選択UI

対象:

- `button.movebutton`
- `button[data-tooltip^="switchpokemon|"]`
- `button[data-tooltip^="allypokemon|"]`
- `button[data-tooltip^="activepokemon|"]`

`MutationObserver`は`childList`、`subtree`、`characterData`を監視します。変更するのは直下の表示テキストノードだけです。

契約:

```text
display_text_only: true
mutates_commands: false
mutates_tooltips: false
preserves_unknown_names: true
```

ニックネームと未知名は元の表示を保持します。

## T1-10 サーバープロトコル不変テスト

`scripts/test-japanese-protocol-invariants.js` は同じcanonical English入力を、生プロトコル保存用と表示用へ複製します。

期待結果:

- `|request|`は変更なし
- `|switch|`は変更なし
- `|move|`は変更なし
- `/choose move 1`は変更なし
- `/switch 1`は変更なし
- tooltipsは変更なし
- `Thunderbolt`の表示だけが`10まんボルト`
- `Pikachu`の表示だけが`ピカチュウ`

`scripts/smoke-bss-protocol-invariants.py` は日本語設定有効下の実サーバーで同じ境界を確認します。

## T1-11 foul-play受信ログ不変テスト

### opt-in raw記録

`scripts/patch-foul-play-raw-receive-log.py` は、固定foul-playの`PSWebsocketClient.receive_message()`へテスト専用の記録処理を追加します。

```text
FOUL_PLAY_RAW_RECEIVE_LOG=/app/.runtime/foul-play-received.jsonl
```

設定時のみ、`websocket.recv()`が返した文字列をJSONLへ保存します。保存後も同じ`message`をそのまま返します。

環境変数がない通常起動では:

- ファイルを開かない
- ログを書かない
- メッセージを加工しない
- battle処理を変更しない

### 単体テスト

`scripts/test-foul-play-raw-receive-log.py` は次を確認します。

- 複数行フレームを完全一致で返す
- JSONLから復元した`message`が完全一致する
- `received_at_ns`が整数
- 環境変数なしでは記録件数が増えない

### 実戦smoke

`scripts/smoke-bss-foul-play-input-invariants.py` は`FoulPlayAI`へ実際にchallengeします。

検査手順:

1. challenger側で日本語設定を有効化
2. 日本語の`/language`応答を確認
3. rawログの開始byte offsetを記録
4. BSSのteam previewと最初のmoveを実行
5. offset以後の記録だけを読む
6. 当該battle roomを含むフレームだけを抽出
7. Bot側の`|request|`・`|switch|`・`|move|`を解析
8. species・moves・abilities・itemsの全カテゴリが存在することを確認
9. battle scoped frameに日本語文字が一つもないことを確認
10. move nameとmove IDの正規化関係を確認

検査フィールド:

| Category | Bot受信フィールド |
| --- | --- |
| species | `ident`, `details`, `|switch|` details |
| moves | active `move`, active `id`, side `moves`, `|move|` name |
| abilities | `baseAbility` |
| items | `item` |

専用artifact:

```text
bss-foul-play-input-invariant-diagnostics
```

含まれる診断:

- `bss-foul-play-input-invariants.log`
- `bss-foul-play-input-invariants.status`
- `foul-play-received.jsonl`

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

表示名API、サーバー辞書、raw auditは互いに独立させます。raw auditは翻訳元や実行時データ経路として使用しません。

## 固定リビジョン

現在のクライアント:

```text
80c72741b52e91d35ee778982a936ea42526c078
```

上流基点:

```text
085dfabd9bc53c730ac459edf5c28088677adfc2
```

固定foul-play:

```text
25c976f05cbf2880eaa579afd6db1dcb2c3b57c6
```

T1-11はクライアントSHAを変更しません。

## 必須テスト

```bash
node scripts/test-japanese-protocol-invariants.js \
  --client-root /opt/pokemon-showdown-client

.venv/bin/python scripts/test-foul-play-local-login.py
.venv/bin/python scripts/test-foul-play-battle-fallbacks.py
.venv/bin/python scripts/test-foul-play-raw-receive-log.py

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

Render smokeは次を連続して実行します。

- Docker build
- 固定クライアント検証
- T1-10複製入力テスト
- Bot identity
- T1-11 foul-play受信ログ実戦smoke
- T1-10実サーバープロトコルsmoke
- 通常BSS対戦
- 瀕死後強制交代
- access gate
- 固定クライアント配信
- iPadサイズ画面取得

## 障害対応

### raw receive logが作成されない

1. containerに`FOUL_PLAY_RAW_RECEIVE_LOG`が設定されているか確認
2. `scripts/patch-foul-play-raw-receive-log.py`がDocker buildで適用されたか確認
3. `scripts/test-foul-play-raw-receive-log.py`を実行
4. foul-playがnamed login済みか確認
5. 出力先の親ディレクトリ`.runtime`が存在するか確認

### T1-11でカテゴリ不足になる

1. raw artifactに当該battle roomが含まれるか確認
2. `|request|`がteam previewまで到達しているか確認
3. Botの固定teamにabilityとitemが設定されているか確認
4. 最初の`|switch|`と`|move|`まで進んだか確認
5. challenge終了前にログを読んでいないか確認

### 日本語混入を検出する

1. `foul-play-received.jsonl`の当該battle roomを確認
2. `|request|`・`|switch|`・`|move|`のどこに混入したか特定
3. 表示名APIがWebSocket payload作成へ使用されていないか確認
4. server dictionaryがbattle protocolを置換していないか確認
5. 修正後にT1-10とT1-11を両方再実行

### Botが停止する

1. `.runtime/foul-play.log`を確認
2. `test-foul-play-local-login.py`を実行
3. `test-foul-play-battle-fallbacks.py`を実行
4. `test-foul-play-raw-receive-log.py`を実行
5. 通常BSSとpost-faint smokeを実行

## ロールバック

T1-11は表示機能やクライアントSHAを変更しません。

raw audit実装自体に問題がある場合:

1. T1-11のserver squash mergeをrevertするPRを作る
2. T1-10時点のruntime動作を維持する
3. protocolや表示機能を変えてテストを回避しない
4. patch適用点、JSONL書き込み、battle room抽出、offset処理を先に修正する

T1-09のUI連携を戻す場合のクライアントSHA:

```text
523a5fb38255916f6fb7bcd4b5b3ccaa5414f6eb
```

T1-05の切替anchor:

```text
72d861147333739363cdb3210ff014ba418ab178
```

## 変更レビューのチェックリスト

- [ ] `data/`と`sim/`に変更がない
- [ ] クライアントSHAを意図せず変更していない
- [ ] raw記録は`FOUL_PLAY_RAW_RECEIVE_LOG`設定時のみ有効
- [ ] `receive_message()`の返り値は受信フレームと完全一致
- [ ] Bot側`|request|`・`|switch|`・`|move|`を実戦で取得した
- [ ] species・moves・abilities・itemsをすべて検査した
- [ ] Bot側battle frameに日本語文字がない
- [ ] T1-10サーバープロトコル検証が継続成功
- [ ] `/choose`・`/team`・Import/Exportを変更していない
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
