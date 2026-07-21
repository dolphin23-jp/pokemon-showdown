# Japanese localization operations

この文書は、個人用 Pokémon Showdown + foul-play 環境における日本語化の運用正本です。現在の構成、更新方法、検証、障害対応、切り戻しをまとめます。

## 現在の状態

Phase 1 T1-07 時点では、次の状態です。

- ブラウザの既定入口は `/client.html`
- クライアントは `dolphin23-jp/pokemon-showdown-client` の完全SHAからDockerビルドされる
- 固定情報は `config/pokemon-showdown-client.json` に保存される
- 完成したクライアントは `/opt/pokemon-showdown-client` に格納される
- 実行時に `play.pokemonshowdown.com` からHTMLや未一致アセットを取得しない
- ブラウザは同一オリジンの `/showdown` を通じてローカルサーバーへ接続する
- ブラウザユーザーはnamedログイン後に一度だけ `/updatesettings {"language":"japanese"}` を送る
- クライアントは表示専用の `window.PSDisplayNames` を公開する
- 日本語名データの受け口は `window.BattleJapaneseDisplayNames`
- T1-07ではAPI骨格のみで、日本語名マップはまだ生成しない
- 未登録名はcanonical EnglishのDex名へフォールバックする
- foul-playは英語の正規化IDとプロトコルを使い、ブラウザ表示APIを通らない

T1-07の詳細は[表示名API作業記録](./phase-1-t1-07-display-name-api.md)を参照してください。Phase 1 T1-06でこの正本文書を導入し、以後のタスクで現在状態を更新します。

## 構成

```text
Browser
  -> launcher : $PORT / $LAUNCHER_PORT
       -> /client.html and explicit client assets
          /opt/pokemon-showdown-client
          -> window.PSDisplayNames
             -> window.BattleJapaneseDisplayNames (T1-08以降)
       -> /showdown
          Pokemon Showdown server : $SHOWDOWN_PORT (default 8000)

foul-play
  -> Pokemon Showdown server : $SHOWDOWN_PORT
  -> poke-engine through its pinned Python dependency
```

主なファイルは次のとおりです。

| 役割 | ファイル |
| --- | --- |
| Render定義 | `render.yaml` |
| コンテナ構築 | `Dockerfile` |
| 起動監視 | `scripts/render-start.sh` |
| ブラウザ入口と `/showdown` プロキシ | `scripts/launcher-server.js` |
| 固定クライアントHTML・静的資産配信 | `scripts/pinned-client-preload.js` |
| クライアント固定情報 | `config/pokemon-showdown-client.json` |
| 固定フォーク・SHA・上流基点検証 | `scripts/check-pinned-client.py` |
| 完成物と表示名API契約の検証 | `scripts/check-built-client.py` |
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

### クライアント表示名API

固定クライアントは、次の表示専用関数を `window.PSDisplayNames` に公開します。

- `displaySpeciesName(...)`
- `displayMoveName(...)`
- `displayAbilityName(...)`
- `displayItemName(...)`

各関数は既存のDexで入力を解決し、正規化IDをキーとして `window.BattleJapaneseDisplayNames` を参照します。対応する日本語名がなければcanonical EnglishのDex名を返します。

このAPIは表示文字列を返すだけです。Dexオブジェクト、入力、ID、保存データ、通信データは変更しません。T1-08で機械生成マップを追加するまで、通常は英語名が返ります。

## 絶対に変えない境界

以下は日本語化しません。

- `data/` と `sim/` にある辞書キー、species ID、move ID、item ID、ability ID
- WebSocketの対戦プロトコル
- `/choose` の内容
- `/team` の内容
- Team Import/Export形式
- challenge format ID
- foul-playへ渡すポケモン、技、持ち物、特性、状態のID
- Rust `poke-engine` へ渡すID

日本語名は表示専用APIの戻り値としてのみ使用し、内部検索・保存・通信のキーにはしません。表示名から英語IDを逆生成する設計も禁止します。

## クライアント固定情報

`config/pokemon-showdown-client.json` は、採用するフォークコミットと、その由来となる上流基点を分けて記録します。

- `commit`: 実際にDockerビルドするフォークSHA
- `commit_date`: そのフォークコミットの日付
- `upstream_base_commit`: フォーク変更の基点となる上流SHA
- `upstream_base_commit_date`: 上流基点の日付
- `runtime_delivery_changed`: T1-05の切り替え後は常に `true`

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
6. 必須4テストを実行する
7. Node.js CIとRender smoke成功後にsquash mergeする

### 日本語サーバー辞書の変更

1. `translations/japanese/` で英語原文キーと日本語訳を対応させる
2. protocol文字列やIDを置換しない
3. `scripts/smoke-bss-battle.py` の実サーバー `/language` 確認を通す
4. 必須4テストを実行する

### 固定クライアントの更新

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

9. `/client.html`、代表的なJS・CSS・config、404境界、iPadサイズ画面を確認する
10. 必須4テストを通してからマージする

`/opt/pokemon-showdown-client` 内の生成物をサーバーリポジトリへ手作業でコピーしません。Dockerのclient-builder stageを唯一の生成経路とします。

## 必須テスト

日本語化タスクを完了するたびに、少なくとも次の4テストを実行します。

```bash
.venv/bin/python scripts/test-foul-play-local-login.py
.venv/bin/python scripts/test-foul-play-battle-fallbacks.py
.venv/bin/python scripts/smoke-bss-battle.py --bot FoulPlayAI --port 8000 --timeout 90
.venv/bin/python scripts/smoke-bss-faint-recovery.py --bot FoulPlayAI --port 8000 --timeout 150
```

クライアント配信に関係する変更では、さらに次を実行します。

```bash
node scripts/test-launcher-japanese-language.js
node scripts/test-launcher-pinned-client.js
python3 scripts/check-pinned-client.py --verify-remote
python3 scripts/check-localization-docs.py
```

Render smokeはDockerビルド、固定成果物検証、Bot対戦、強制交代回復、クライアント配信、画面キャプチャを一続きで確認します。

## 稼働確認

### ヘルスチェック

```bash
curl --fail https://<service-host>/health
```

応答には `ok: true` とformatが含まれます。これは到達確認であり、Bot対戦完遂の代わりにはなりません。

### クライアント配信元

認証後の `/client.html` とローカル資産には次のヘッダーが付きます。

```text
X-Pokemon-Showdown-Client-Source: pinned-local
```

表示名APIは `/js/battle-display-names.js` から同じヘッダー付きで配信されます。未知パスが公式サイトの内容を返す場合はT1-05の境界が壊れています。

### ログ

- `.runtime/showdown.log`
- `.runtime/foul-play.log`
- `.runtime/launcher.log`

最初に停止したコンポーネントと、その直前の例外を確認します。

## 障害時の切り分け

### クライアントが白画面になる

1. `/client.html` のHTTP状態と `pinned-local` ヘッダーを確認する
2. 404になった同一オリジン資産を特定する
3. `scripts/check-built-client.py` で固定成果物を再検証する
4. HTMLが公式ホストのscript・image・stylesheetを参照していないか確認する
5. SHA更新直後なら固定SHAと生成物の組み合わせを疑う

### 表示名APIが見つからない

1. `/js/battle-display-names.js` が200を返すか確認する
2. `window.PSDisplayNames` が存在するか確認する
3. `config/japanese-display-name-api.json` とビルドマニフェストを確認する
4. T1-07では日本語マップが未生成であり、英語フォールバックが正常であることを区別する

### Botがログインしない

1. `FOUL_PLAY_USERNAME` を確認する
2. `scripts/test-foul-play-local-login.py` を実行する
3. foul-playの送信が `/trn FoulPlayAI,0,` のような英語名・正規化形式のままか確認する
4. 表示名APIをfoul-play経路へ流用していないか確認する

### Botが対戦中に停止する

1. `foul-play.log` とbattle protocolを確認する
2. `scripts/test-foul-play-battle-fallbacks.py` を実行する
3. 通常対戦smokeと瀕死後回復smokeを実行する
4. 日本語表示名がfoul-playまたは`poke-engine`入力に混入していないか確認する

## ロールバック

ロールバックはforce pushではなくPRで行います。

### クライアント更新だけを戻す

1. 直前に成功していた完全SHAを特定する
2. `commit` と `commit_date` を戻す
3. 対応する `upstream_base_commit` と `upstream_base_commit_date` を確認する
4. `runtime_delivery_changed` は `true` のまま維持する
5. 固定フォーク検証、Dockerビルド、完成物検証、必須4テストを実行する
6. ロールバックPRをマージし、Renderデプロイを確認する

Phase 1で最初に採用した既知の上流SHAは次です。

```text
085dfabd9bc53c730ac459edf5c28088677adfc2
```

T1-07の表示名APIを含む最初のフォークSHAは次です。

```text
1a5d96a4c05f0f4da766de877f3219b68c51f158
```

障害内容に応じ、直近の既知正常版を優先します。

### T1-05の既定切り替え自体を戻す

SHAを戻しても復旧しない重大障害に限ります。

1. T1-05のsquash merge `72d861147333739363cdb3210ff014ba418ab178` を基準にrevert PRを作る
2. 競合時は `launcher-server.js`、`pinned-client-preload.js`、Docker設定を明示的に復旧する
3. 公式クライアントへの実行時依存再導入は一時的な緊急措置とする
4. 必須4テストとアクセスゲートを確認してからマージする

## 変更レビューのチェックリスト

- [ ] `data/` と `sim/` に変更がない
- [ ] 正規化IDを日本語へ置換していない
- [ ] `/choose`、`/team`、Import/Exportを変更していない
- [ ] foul-playと`poke-engine`の入力は英語IDのまま
- [ ] 表示変換は `window.PSDisplayNames` に限定されている
- [ ] クライアントは完全SHAで固定されている
- [ ] フォークSHAの上流基点を説明できる
- [ ] `/client.html` と表示名API資産が`pinned-local`を返す
- [ ] 未知パスが404になる
- [ ] 必須4テストが成功している
- [ ] Node.js CIとRender smokeが成功している
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

次のT1-08では日本語表示名マップを機械生成します。ここに記載したID・protocol境界は維持します。
