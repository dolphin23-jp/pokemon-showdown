# Japanese localization operations

この文書は、個人用 Pokémon Showdown + foul-play 環境における日本語化の運用正本です。現在の構成、更新方法、検証、障害対応、切り戻しをまとめます。

## 現在の状態

Phase 1 T1-10 時点では、次の状態です。

- ブラウザの既定入口は `/client.html`
- クライアントは `dolphin23-jp/pokemon-showdown-client` の完全SHAからDockerビルドされる
- 固定情報は `config/pokemon-showdown-client.json` に保存される
- 完成したクライアントは `/opt/pokemon-showdown-client` に格納される
- 実行時に `play.pokemonshowdown.com` からHTMLや未一致アセットを取得しない
- ブラウザは同一オリジンの `/showdown` を通じてローカルサーバーへ接続する
- ブラウザユーザーはnamedログイン後に一度だけ `/updatesettings {"language":"japanese"}` を送る
- クライアントは表示専用の `window.PSDisplayNames` を公開する
- 日本語名データは `window.BattleJapaneseDisplayNames` の4表に機械生成される
- 技選択ボタンと交代・選出・対象選択ボタンの表示名を日本語化する
- 未登録名、フォーム固有名、ニックネームはcanonical Englishまたは元の表示へフォールバックする
- 同一入力を生プロトコルと表示用に複製し、表示だけが日本語化されることを機械検証する
- 実サーバーの `|request|`、`|switch|`、`|move|`、`/choose`、`/team` はcanonical Englishのまま検証される
- foul-playと`poke-engine`は英語の正規化IDとbattle protocolを使い、表示APIを通らない

作業記録は次を参照してください。

- [T1-07 表示名API](./phase-1-t1-07-display-name-api.md)
- [T1-08 生成マップ](./phase-1-t1-08-generated-name-maps.md)
- [T1-09 対戦選択UI](./phase-1-t1-09-battle-controls.md)
- [T1-10 プロトコル不変テスト](./phase-1-t1-10-protocol-invariants.md)

Phase 1 T1-06でこの正本文書を導入し、以後のタスクで現在状態を更新します。

## 構成

```text
Browser
  -> launcher : $PORT / $LAUNCHER_PORT
       -> /client.html and explicit client assets
          /opt/pokemon-showdown-client
          -> battle-display-names.js
             -> window.BattleJapaneseDisplayNames
             -> window.PSDisplayNames
             -> battle choice button text only
       -> /showdown
          Pokemon Showdown server : $SHOWDOWN_PORT (default 8000)
          -> raw |request|, |switch|, |move| remain canonical English

foul-play
  -> Pokemon Showdown server : $SHOWDOWN_PORT
  -> poke-engine through its pinned Python dependency

T1-10 verification
  -> duplicated fixture: raw protocol copy vs rendered button text
  -> live WebSocket: Japanese setting enabled, battle protocol remains English
```

主なファイルは次のとおりです。

| 役割 | ファイル |
| --- | --- |
| Render定義 | `render.yaml` |
| Render smoke | `.github/workflows/render-smoke.yml` |
| コンテナ構築 | `Dockerfile` |
| 起動監視 | `scripts/render-start.sh` |
| ブラウザ入口と `/showdown` プロキシ | `scripts/launcher-server.js` |
| 固定クライアントHTML・静的資産配信 | `scripts/pinned-client-preload.js` |
| クライアント固定情報 | `config/pokemon-showdown-client.json` |
| 固定フォーク・SHA・上流基点検証 | `scripts/check-pinned-client.py` |
| 完成物・表示API・生成マップ・UI契約検証 | `scripts/check-built-client.py` |
| 複製入力の表示／プロトコル不変テスト | `scripts/test-japanese-protocol-invariants.js` |
| 実WebSocketプロトコル不変smoke | `scripts/smoke-bss-protocol-invariants.py` |
| 日本語サーバー辞書 | `translations/japanese/` |
| Phase 1構成検証 | `scripts/check-phase1-baseline.py` |
| 文書整合性検証 | `scripts/check-localization-docs.py` |

`pinned-client-preload.js` という名前はT1-04の履歴に由来します。T1-05以降はNodeのpreloadではなく、ランチャーから通常のモジュールとして読み込みます。

## 日本語化される場所

### ランチャー

入口、アクセスキー画面、構築ライブラリは `scripts/launcher-server.js` 内の表示専用HTMLです。

### サーバー応答

`translations/japanese/` の辞書は、ブラウザユーザーが日本語設定を選択した後のサーバーコマンド応答などに使われます。順序は次のとおりです。

1. `/trn <name>,0,` でnamedログインする
2. named状態を確認する
3. `/updatesettings {"language":"japanese"}` を一度だけ送る

サーバーコマンド応答が日本語でも、battle protocolは日本語化しません。

### クライアント表示名API

固定クライアントは、次の表示専用関数を `window.PSDisplayNames` に公開します。

- `displaySpeciesName(...)`
- `displayMoveName(...)`
- `displayAbilityName(...)`
- `displayItemName(...)`

各関数は既存のDexで入力を解決し、正規化IDをキーとして `window.BattleJapaneseDisplayNames` を参照します。対応する日本語名がなければcanonical EnglishのDex名を返します。

このAPIは表示文字列を返すだけです。Dexオブジェクト、入力、ID、保存データ、通信データは変更しません。

### 日本語表示名マップ

T1-08では、クライアントビルド時に `build-tools/generate-japanese-display-names.js` が日本語名を機械生成します。

- 出典: `PokeAPI/pokeapi`
- 固定出典SHA: `227b573712414a86ba299d322fa398fbb2893edc`
- 言語: PokeAPI language ID `11`
- 生成対象: species、moves、abilities、items
- 埋め込み先: `play.pokemonshowdown.com/js/battle-display-names.js`
- メタデータ: `play.pokemonshowdown.com/js/battle-display-names.meta.json`

生成器は英語identifierを小文字英数字IDへ正規化し、そのIDを日本語表示名のキーにします。生成件数がspecies 1000、moves 800、abilities 250、items 1500を下回る場合、衝突がある場合、固定出典を取得できない場合はビルドを失敗させます。

生成物は手作業で編集しません。出典を更新する場合は完全SHAを更新し、件数差分、代表名、ID境界、クライアントCI、サーバーDocker完成物を一体で確認します。

### 対戦選択ボタン

T1-09では、生成済み表示名を次の対戦操作UIへ適用します。

- `button.movebutton`: 通常技、Zワザ、ダイマックス技、キョダイマックス技
- `button[data-tooltip^="switchpokemon|"]`: 交代、選出、手持ち一覧
- `button[data-tooltip^="allypokemon|"]`: 味方ポケモン
- `button[data-tooltip^="activepokemon|"]`: 技対象となる場のポケモン

技ボタンは `displayMoveName(...)`、ポケモンボタンは `displaySpeciesName(...)` を使用します。ニックネームや未知の文字列は変更しません。

Preactが描画した後の要素へ対応するため、`MutationObserver` が `childList`、`subtree`、`characterData` を監視します。ただし変更するのはボタン直下の表示テキストノードだけです。

次は必ずcanonical Englishのまま維持します。

- `data-cmd`
- `data-tooltip`
- request JSON
- move indexとswitch index
- WebSocket battle protocol
- `/choose` と `/team`

表示契約は `display_text_only: true`、`mutates_commands: false`、`mutates_tooltips: false`、`preserves_unknown_names: true` です。

## T1-10 サーバープロトコル不変テスト

T1-10は新しい日本語表示面を追加しません。T1-09までに定義した表示専用境界を、複製入力テストと実WebSocketテストで固定します。

### 複製入力テスト

`scripts/test-japanese-protocol-invariants.js` は、固定クライアントの `battle-display-names.js` を読み込み、同じcanonical English入力を次の2系統へ渡します。

1. 生プロトコルの保存コピー
2. 日本語表示名を適用する合成対戦ボタン

入力例は次です。

```text
|request|{"active":[{"moves":[{"move":"Thunderbolt","id":"thunderbolt"}]}]...}
|switch|p1a: Pikachu|Pikachu, L50|100/100
|move|p1a: Pikachu|Thunderbolt|p2a: Charizard
```

期待結果は次です。

- 生 `|request|`、`|switch|`、`|move|` は入力と完全一致
- request JSONオブジェクトは変更なし
- `/choose move 1` と `/switch 1` は変更なし
- `move|Thunderbolt|0` と `switchpokemon|0` は変更なし
- 表示テキストだけが `10まんボルト` と `ピカチュウ` になる
- `MutationObserver`による再描画後も生プロトコルとコマンドは変更されない

### 実WebSocketテスト

`scripts/smoke-bss-protocol-invariants.py` は実サーバーへ接続し、日本語設定を有効化して `/language` の日本語応答を確認した状態で、`FoulPlayAI` と実際に対戦します。

次を必須とします。

- raw `|request|` を1件以上取得
- raw `|switch|` を1件以上取得
- raw `|move|` を1件以上取得
- `/team 123456` をcanonical Englishのまま送信
- `/choose move <index>` をcanonical Englishのまま送信
- critical protocolとoutbound commandに日本語表示文字がない
- request内のmove IDが英語move nameの正規化IDと一致する

日本語サーバー設定が有効な状態でこの検証を行うため、「日本語設定が無効だからprotocolが英語だった」という偽陽性を避けます。

## 絶対に変えない境界

以下は日本語化しません。

- `data/` と `sim/` にある辞書キー、species ID、move ID、item ID、ability ID
- WebSocketの対戦プロトコル
- `|request|`、`|switch|`、`|move|`
- `/choose` の内容
- `/team` の内容
- Team Import/Export形式
- challenge format ID
- foul-playへ渡すポケモン、技、持ち物、特性、状態のID
- Rust `poke-engine` へ渡すID

日本語名は表示専用APIと表示テキスト置換にのみ使用し、内部検索・保存・通信のキーにはしません。表示名から英語IDを逆生成する設計も禁止します。

## クライアント固定情報

`config/pokemon-showdown-client.json` は、採用するフォークコミットと、その由来となる上流基点を分けて記録します。

- `commit`: 実際にDockerビルドするフォークSHA
- `commit_date`: そのフォークコミットの日付
- `upstream_base_commit`: フォーク変更の基点となる上流SHA
- `upstream_base_commit_date`: 上流基点の日付
- `runtime_delivery_changed`: T1-05の切り替え後は常に `true`

T1-10はテスト追加のみであり、T1-09のクライアントSHAを維持します。

```text
80c72741b52e91d35ee778982a936ea42526c078
```

上流基点は次です。

```text
085dfabd9bc53c730ac459edf5c28088677adfc2
```

`scripts/check-pinned-client.py --verify-remote` は、フォーク関係、各SHAと日付、フォークSHAが上流基点を祖先に持つことを確認します。

## Renderでの運用

`render.yaml` はDockerサービスを定義し、`/health` をヘルスチェックに使います。`scripts/render-start.sh` はShowdown、foul-play、launcherを起動し、いずれかが停止した場合はコンテナを終了させます。

最低限確認する環境変数は次のとおりです。

- `ACCESS_TOKEN`: 個人用入口のアクセスキー
- `DEFAULT_PLAYER_NAME`: ブラウザの既定名
- `FOUL_PLAY_USERNAME`: Bot名
- `FOUL_PLAY_FORMAT`: 対戦形式
- `SHOWDOWN_PORT`: 内部サーバーポート。通常は8000

`PORT` はRenderからランチャーへ渡され、起動時に `LAUNCHER_PORT` へ移されます。Showdownサーバーと同じポートへ割り当てません。

## 通常の更新フロー

### サーバーまたはランチャーの変更

1. `master` の最新コミットから作業ブランチを作る
2. `data/` と `sim/` を変更していないことを確認する
3. 対象の単体テストを追加または更新する
4. Phase 1検査を実行する
5. Dockerイメージをクリーンビルドする
6. 必須テストを実行する
7. Node.js CIとRender smoke成功後にsquash mergeする

### 日本語サーバー辞書の変更

1. `translations/japanese/` で英語原文キーと日本語訳を対応させる
2. protocol文字列やIDを置換しない
3. `scripts/smoke-bss-battle.py` の実サーバー `/language` 確認を通す
4. プロトコル不変smokeを含む必須テストを実行する

### 固定クライアント・生成マップ・表示面の更新

クライアント更新はブランチ名ではなく完全な40文字SHAで固定します。

1. 所有フォークに採用対象コミットが存在することを確認する
2. `commit` と `commit_date` を更新する
3. 上流基点が変わる場合だけ `upstream_base_commit` と `upstream_base_commit_date` を更新する
4. `fork_repository` と `upstream_repository` は変更しない
5. `runtime_delivery_changed` は `true` のままにする
6. リモート固定情報を検証する

```bash
python3 scripts/check-pinned-client.py --verify-remote
```

7. Dockerイメージをキャッシュなしでビルドする

```bash
docker build --no-cache --tag pokemon-showdown-ai:localization-check .
```

8. コンテナ内の完成物を検証する

```bash
docker run --rm --entrypoint python3 pokemon-showdown-ai:localization-check \
  /app/scripts/check-built-client.py \
  --client-root /opt/pokemon-showdown-client \
  --pin-file /app/config/pokemon-showdown-client.json
```

9. 複製入力のプロトコル不変テストを実行する

```bash
docker run --rm --entrypoint node pokemon-showdown-ai:localization-check \
  /app/scripts/test-japanese-protocol-invariants.js \
  --client-root /opt/pokemon-showdown-client
```

10. `battle-display-names.meta.json` の出典SHA、言語ID、4表の件数を確認する
11. `data-cmd`、`data-tooltip`、request JSON、protocolが英語のままか確認する
12. `/client.html`、代表的なJS・CSS・config、404境界、iPadサイズ画面を確認する
13. 必須テストを通してからマージする

`/opt/pokemon-showdown-client` 内の生成物をサーバーリポジトリへ手作業でコピーしません。Dockerのclient-builder stageを唯一の生成経路とします。

## 必須テスト

日本語化タスクを完了するたびに、少なくとも次を実行します。

```bash
node scripts/test-japanese-protocol-invariants.js \
  --client-root /opt/pokemon-showdown-client
.venv/bin/python scripts/test-foul-play-local-login.py
.venv/bin/python scripts/test-foul-play-battle-fallbacks.py
.venv/bin/python scripts/smoke-bss-protocol-invariants.py \
  --bot FoulPlayAI --port 8000 --timeout 90
.venv/bin/python scripts/smoke-bss-battle.py \
  --bot FoulPlayAI --port 8000 --timeout 90
.venv/bin/python scripts/smoke-bss-faint-recovery.py \
  --bot FoulPlayAI --port 8000 --timeout 150
```

クライアント配信に関係する変更では、さらに次を実行します。

```bash
node scripts/test-launcher-japanese-language.js
node scripts/test-launcher-pinned-client.js
python3 scripts/check-pinned-client.py --verify-remote
python3 scripts/check-localization-docs.py
```

Render smokeはDockerビルド、固定成果物検証、複製入力テスト、実WebSocketプロトコル不変テスト、Bot通常対戦、強制交代回復、クライアント配信、画面キャプチャを一続きで確認します。

## 稼働確認

### ヘルスチェック

```bash
curl --fail https://<service-host>/health
```

応答には `ok: true` とformatが含まれます。これは到達確認であり、Bot対戦完遂やプロトコル不変確認の代わりにはなりません。

### クライアント配信元

認証後の `/client.html` とローカル資産には次のヘッダーが付きます。

```text
X-Pokemon-Showdown-Client-Source: pinned-local
```

表示名API、生成マップ、対戦選択UI連携は `/js/battle-display-names.js` から同じヘッダー付きで配信されます。未知パスが公式サイトの内容を返す場合はT1-05の境界が壊れています。

### ログとCI成果物

- `.runtime/showdown.log`
- `.runtime/foul-play.log`
- `.runtime/launcher.log`
- `bss-protocol-invariant-diagnostics`
- `bss-smoke-diagnostics`
- `bss-faint-smoke-diagnostics`
- `phase1-localization-artifacts`

最初に停止したコンポーネントと、その直前の例外を確認します。

## 障害時の切り分け

### クライアントが白画面になる

1. `/client.html` のHTTP状態と `pinned-local` ヘッダーを確認する
2. 404になった同一オリジン資産を特定する
3. `scripts/check-built-client.py` で固定成果物を再検証する
4. HTMLが公式ホストのscript・image・stylesheetを参照していないか確認する
5. SHA更新直後なら固定SHAと生成物の組み合わせを疑う

### 対戦選択ボタンが英語のままになる

1. `/js/battle-display-names.js` が200を返すか確認する
2. `window.PSDisplayNames` と `window.BattleJapaneseDisplayNames` が存在するか確認する
3. 対象ボタンがT1-09の4セレクタに一致するか確認する
4. 対象文字列がニックネームまたは生成元にないフォーム名でないか確認する
5. `MutationObserver` が動作し、`childList`、`subtree`、`characterData` を監視しているか確認する
6. `scripts/check-built-client.py` でソースとbundleのT1-09契約を確認する

### protocol invariant smokeが失敗する

1. `bss-protocol-invariant-diagnostics` を確認する
2. 日本語 `/language` 応答まで到達しているか確認する
3. `|request|`、`|switch|`、`|move|` のどの種類が不足したか確認する
4. critical lineまたはoutbound `/choose`・`/team`へ日本語が混入していないか確認する
5. request内のmove nameとmove IDの正規化関係を確認する
6. `scripts/test-japanese-protocol-invariants.js` が同じ変更で成功するか確認する

### 日本語名が英語へフォールバックする

1. `battle-display-names.meta.json` の4表件数を確認する
2. 対象がPokeAPIのspecies表にないフォーム固有名か確認する
3. `scripts/check-built-client.py` が固定出典SHAと件数を検証できるか確認する

### 選択操作が失敗する

1. ボタンの `data-cmd` が `/choose move <index>` または `/switch <index>` のままか確認する
2. `data-tooltip` がcanonical Englishのままか確認する
3. WebSocketの `/choose` payloadに日本語文字列が混入していないか確認する
4. 複製入力テストと実WebSocketプロトコル不変smokeを再実行する
5. 既存の通常対戦smokeと瀕死後回復smokeを再実行する

### Botがログインしない

1. `FOUL_PLAY_USERNAME` を確認する
2. `scripts/test-foul-play-local-login.py` を実行する
3. foul-playの送信が `/trn FoulPlayAI,0,` のような英語名・正規化形式のままか確認する
4. 表示名APIをfoul-play経路へ流用していないか確認する

### Botが対戦中に停止する

1. `foul-play.log` とbattle protocolを確認する
2. `scripts/test-foul-play-battle-fallbacks.py` を実行する
3. protocol invariant、通常対戦、瀕死後回復の3つのsmokeを実行する
4. 日本語表示名がfoul-playまたは`poke-engine`入力に混入していないか確認する

## ロールバック

ロールバックはforce pushではなくPRで行います。

### T1-10のテスト追加を戻す

T1-10はruntime機能やクライアントSHAを変更しません。テスト自体に誤りがある場合は、T1-10のサーバーsquash mergeをrevertするPRを作り、T1-09のruntime状態を維持します。

テスト失敗を回避するためにprotocolや表示機能を変更してはいけません。まずfixture、WebSocket観測条件、Bot再挑戦待機、タイムアウトを検証します。

### T1-09の対戦選択UI連携を戻す

直前のT1-08クライアントSHAへ固定を戻します。

```text
523a5fb38255916f6fb7bcd4b5b3ccaa5414f6eb
```

1. `commit` と `commit_date` をT1-08へ戻す
2. `upstream_base_commit` と `upstream_base_commit_date` を維持する
3. `runtime_delivery_changed` は `true` のまま維持する
4. 固定フォーク検証、Dockerビルド、完成物検証、必須テストを実行する
5. ロールバックPRをマージし、Renderデプロイを確認する

T1-07の表示名APIのみを含む既知正常クライアントSHAは次です。

```text
1a5d96a4c05f0f4da766de877f3219b68c51f158
```

T1-09およびT1-10で使用する現在のクライアントSHAは次です。

```text
80c72741b52e91d35ee778982a936ea42526c078
```

Phase 1で最初に採用した上流基点SHAは次です。

```text
085dfabd9bc53c730ac459edf5c28088677adfc2
```

### T1-05の既定切り替え自体を戻す

SHAを戻しても復旧しない重大障害に限ります。

1. T1-05のsquash merge `72d861147333739363cdb3210ff014ba418ab178` を基準にrevert PRを作る
2. 競合時は `launcher-server.js`、`pinned-client-preload.js`、Docker設定を明示的に復旧する
3. 公式クライアントへの実行時依存再導入は一時的な緊急措置とする
4. 必須テストとアクセスゲートを確認してからマージする

## 変更レビューのチェックリスト

- [ ] `data/` と `sim/` に変更がない
- [ ] 正規化IDを日本語へ置換していない
- [ ] `|request|`、`|switch|`、`|move|`がcanonical Englishのまま
- [ ] `/choose`、`/team`、Import/Exportを変更していない
- [ ] foul-playと`poke-engine`の入力は英語IDのまま
- [ ] 表示変換は `window.PSDisplayNames` に限定されている
- [ ] 生成マップは `window.BattleJapaneseDisplayNames` に限定されている
- [ ] 対戦UIでは表示テキストノードだけを変更している
- [ ] `data-cmd` と `data-tooltip` はcanonical Englishのまま
- [ ] ニックネームと未知名を保持する
- [ ] 複製入力テストでraw protocolとrendered textの分離を確認した
- [ ] 日本語設定有効下の実WebSocketプロトコル不変smokeが成功した
- [ ] クライアントと出典は完全SHAで固定されている
- [ ] 生成メタデータの4表件数が下限以上である
- [ ] `/client.html` と表示名API資産が`pinned-local`を返す
- [ ] 未知パスが404になる
- [ ] 既存4回帰テストが成功している
- [ ] Node.js CI、文書CI、Render smokeが成功している
- [ ] ロールバック先を説明できる

## Phase 1の到達点

- T1-00: 挙動・画面・保護境界の基準化
- T1-01: ブラウザユーザーの日本語設定を自動化
- T1-02: クライアントフォークと完全SHAを固定
- T1-03: 固定クライアントをDocker内で再現可能にビルド
- T1-04: 認証下のオプトイン配信経路を追加
- T1-05: `/client.html` を固定ローカル配信へ切り替え、公式実行時プロキシを撤去
- T1-06: 構成、更新、検証、障害対応、ロールバックを正本文書へ統合
- T1-07: 表示専用の日本語名API骨格を固定クライアントへ追加
- T1-08: species、moves、abilities、itemsの日本語表示名マップを固定出典から機械生成
- T1-09: 技選択と交代・選出・対象選択ボタンへ日本語表示名を適用し、操作属性とprotocolを不変に維持
- T1-10: 同一入力のraw protocolとrendered textを比較し、日本語設定有効下でも`|request|`、`|switch|`、`|move|`、`/choose`が不変であることを自動検証
