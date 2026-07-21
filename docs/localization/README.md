# Japanese localization operations

この文書は、個人用 Pokémon Showdown + foul-play 環境における日本語化の正本です。段階別の作業記録ではなく、現在の構成、更新方法、検証、障害対応、切り戻しをまとめています。

## 現在の状態

Phase 1 T1-06 時点では、次の状態です。

- ブラウザの既定入口は `/client.html`
- クライアントは `dolphin23-jp/pokemon-showdown-client` の固定コミットからDockerビルドされる
- 固定情報は `config/pokemon-showdown-client.json` に保存される
- 完成したクライアントは `/opt/pokemon-showdown-client` に格納される
- 実行時に `play.pokemonshowdown.com` からHTMLや未一致アセットを取得しない
- ブラウザは同一オリジンの `/showdown` を通じてローカルサーバーへ接続する
- ブラウザユーザーはnamedログイン後に一度だけ `/updatesettings {"language":"japanese"}` を送る
- foul-playはブラウザを経由せず、英語の正規化IDとプロトコルを使ってローカルサーバーへ直接接続する

段階別の履歴は `docs/localization/phase-1-*.md` に残しますが、運用判断ではこの文書と機械検証結果を優先します。

## 構成

```text
Browser
  -> launcher : $PORT / $LAUNCHER_PORT
       -> /client.html and explicit client assets
          /opt/pokemon-showdown-client
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
| 固定フォーク・SHA検証 | `scripts/check-pinned-client.py` |
| 完成物ハッシュ検証 | `scripts/check-built-client.py` |
| 日本語サーバー辞書 | `translations/japanese/` |
| Phase 1構成検証 | `scripts/check-phase1-baseline.py` |
| この文書の整合性検証 | `scripts/check-localization-docs.py` |

`pinned-client-preload.js` という名前はT1-04の履歴に由来します。T1-05以降はNodeのpreloadとしては使用せず、ランチャーから通常のモジュールとして読み込みます。

## 日本語化される場所

### ランチャー

入口、アクセスキー画面、構築ライブラリは `scripts/launcher-server.js` 内の表示専用HTMLです。

### サーバー応答

`translations/japanese/` の辞書は、ブラウザユーザーが日本語設定を選択した後のサーバーコマンド応答などに使われます。ブラウザ側の自動設定は次の順序を守ります。

1. `/trn <name>,0,` でnamedログインする
2. named状態を確認する
3. `/updatesettings {"language":"japanese"}` を一度だけ送る

### クライアントUIと対戦表示

固定クライアントの画面文言や対戦表示はクライアントフォークで扱います。表示名変換を追加する場合も、変換結果はDOMなどの表示側に限定します。

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

## Renderでの運用

`render.yaml` はDockerサービスを定義し、`/health` をヘルスチェックに使います。`scripts/render-start.sh` は次の3プロセスを起動し、いずれかが停止した場合はコンテナを終了させます。

- Pokémon Showdown server
- foul-play
- launcher

最低限確認する環境変数は次のとおりです。

- `ACCESS_TOKEN`: 個人用入口のアクセスキー。Render側で秘密値として設定する
- `DEFAULT_PLAYER_NAME`: ブラウザの既定名
- `FOUL_PLAY_USERNAME`: Bot名
- `FOUL_PLAY_FORMAT`: 対戦形式
- `SHOWDOWN_PORT`: 内部サーバーポート。通常は既定値8000を使用する

`PORT` はRenderからランチャーへ渡され、起動時に `LAUNCHER_PORT` へ移されます。Pokémon Showdownサーバーと同じポートへ割り当てないでください。

## 通常の更新フロー

### サーバーまたはランチャーの変更

1. `master` の最新コミットから作業ブランチを作る
2. `data/` と `sim/` を変更していないことを確認する
3. 対象の単体テストを追加または更新する
4. Phase 1検査を実行する
5. Dockerイメージをクリーンビルドする
6. 必須4テストを実行する
7. PRのNode.js CIとRender smokeが成功してからsquash mergeする

### 日本語サーバー辞書の変更

1. `translations/japanese/` のみで英語原文キーと日本語訳を対応させる
2. protocol文字列やIDを辞書変更で置換しない
3. `scripts/smoke-bss-battle.py` の実サーバー `/language` 確認を通す
4. 必須4テストを実行する

### 固定クライアントの更新

クライアント更新は、フォークのブランチ名ではなく完全な40文字SHAで固定します。

1. `dolphin23-jp/pokemon-showdown-client` に採用対象コミットが存在することを確認する
2. `config/pokemon-showdown-client.json` の `commit` と `upstream_commit_date` を更新する
3. `fork_repository` と `upstream_repository` は変更しない
4. 既定ローカル配信を維持するため `runtime_delivery_changed` は `true` のままにする
5. 次を実行する

```bash
python3 scripts/check-pinned-client.py --verify-remote
```

6. Dockerイメージをキャッシュなしでビルドする

```bash
docker build --no-cache --tag pokemon-showdown-ai:localization-check .
```

7. コンテナ内の完成物を検証する

```bash
docker run --rm --entrypoint python3 pokemon-showdown-ai:localization-check \
  /app/scripts/check-built-client.py \
  --client-root /opt/pokemon-showdown-client \
  --pin-file /app/config/pokemon-showdown-client.json
```

8. `/client.html`、代表的なJS・CSS・config、404境界、iPadサイズ画面を確認する
9. 必須4テストを通してからマージする

`/opt/pokemon-showdown-client` 内の生成物をサーバーリポジトリへ手作業でコピーしません。Dockerのclient-builder stageを唯一の生成経路とします。

## 必須テスト

日本語化タスクを完了するたびに、少なくとも次の4テストを実行します。

```bash
.venv/bin/python scripts/test-foul-play-local-login.py
.venv/bin/python scripts/test-foul-play-battle-fallbacks.py
.venv/bin/python scripts/smoke-bss-battle.py --bot FoulPlayAI --port 8000 --timeout 90
.venv/bin/python scripts/smoke-bss-faint-recovery.py --bot FoulPlayAI --port 8000 --timeout 150
```

加えて、クライアント配信に関係する変更では次を実行します。

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

応答には `ok: true` と現在のformatが含まれます。これはランチャーへの到達確認であり、Botが対戦を完遂できることの代わりにはなりません。

### クライアント配信元

認証後の `/client.html` とローカル資産には次のヘッダーが付きます。

```text
X-Pokemon-Showdown-Client-Source: pinned-local
```

このヘッダーがなく、または未知パスが公式サイトの内容を返す場合は、T1-05の境界が壊れています。

### ログ

コンテナ内では次を確認します。

- `.runtime/showdown.log`
- `.runtime/foul-play.log`
- `.runtime/launcher.log`

Renderログには起動時から3ファイルの末尾が転送されます。最初に停止したコンポーネントと、その直前の例外を確認してください。

## 障害時の切り分け

### `/health` が失敗する

1. コンテナが起動しているか確認する
2. `launcher.log` を確認する
3. `PORT` と `LAUNCHER_PORT` の競合を確認する
4. `showdown-ai.sh start` の失敗がないか確認する

### クライアントが白画面になる

1. `/client.html` のHTTP状態と `pinned-local` ヘッダーを確認する
2. ブラウザ開発者ツールで404になった同一オリジン資産を特定する
3. `scripts/check-built-client.py` で固定成果物を再検証する
4. HTMLが `play.pokemonshowdown.com` のscript・image・stylesheetを参照していないか確認する
5. クライアントSHA更新直後なら、固定SHAと生成物の組み合わせを疑う

### Botがログインしない

1. `FOUL_PLAY_USERNAME` を確認する
2. `test-foul-play-local-login.py` を実行する
3. foul-playの送信が `/trn FoulPlayAI,0,` のような英語名・正規化形式のままか確認する
4. ブラウザ向け日本語処理をfoul-play経路へ流用していないか確認する

### Botが対戦中に停止する

1. `foul-play.log` とShowdownのbattle protocolを確認する
2. `test-foul-play-battle-fallbacks.py` を実行する
3. 通常対戦smokeと瀕死後回復smokeを両方実行する
4. 日本語表示名がfoul-playまたは`poke-engine`入力に混入していないか確認する

## ロールバック

ロールバックは履歴を破壊するforce pushではなく、PRで行います。

### クライアント更新だけを戻す

最も安全な方法です。

1. 直前に成功していた完全SHAを特定する
2. `config/pokemon-showdown-client.json` の `commit` と `upstream_commit_date` を戻す
3. `runtime_delivery_changed` は `true` のまま維持する
4. 固定フォーク検証、Dockerビルド、完成物検証、必須4テストを実行する
5. ロールバックPRをマージし、Renderの新しいデプロイを確認する

Phase 1で最初に採用した既知のSHAは次です。

```text
085dfabd9bc53c730ac459edf5c28088677adfc2
```

ただし、将来このSHAより新しい既知正常版ができた場合は、直近の正常版を優先します。

### T1-05の既定切り替え自体を戻す

固定クライアント配信コードに重大な問題があり、SHAを戻しても復旧しない場合に限ります。

1. T1-05のsquash merge `72d861147333739363cdb3210ff014ba418ab178` を基準に、現在のmasterへ適用できるrevert PRを作る
2. 将来の変更と競合する場合は自動revertを無理に通さず、`launcher-server.js`、`pinned-client-preload.js`、Docker設定を明示的に復旧する
3. 公式クライアントへの実行時依存を再導入するため、これは一時的な緊急措置として扱う
4. 必須4テストとアクセスゲートを確認してからマージする

履歴上の古いコンテナを直接長期運用せず、原因修正または固定SHAロールバックをmasterへ残してください。

## 変更レビューのチェックリスト

- [ ] `data/` と `sim/` に変更がない
- [ ] 正規化IDを日本語へ置換していない
- [ ] `/choose`、`/team`、Import/Exportを変更していない
- [ ] foul-playと`poke-engine`の入力は英語IDのまま
- [ ] 表示変換は表示専用関数または辞書に限定されている
- [ ] クライアントは完全SHAで固定されている
- [ ] `/client.html` と代表的な資産が`pinned-local`を返す
- [ ] 未知パスが404になる
- [ ] 必須4テストが成功している
- [ ] Node.js CIとRender smokeが成功している
- [ ] ロールバック先の既知正常SHAを説明できる

## Phase 1の到達点

- T1-00: 挙動・画面・保護境界の基準化
- T1-01: ブラウザユーザーの日本語設定を自動化
- T1-02: クライアントフォークと完全SHAを固定
- T1-03: 固定クライアントをDocker内で再現可能にビルド
- T1-04: 認証下のオプトイン配信経路を追加
- T1-05: `/client.html` を固定ローカル配信へ切り替え、公式実行時プロキシを撤去
- T1-06: 構成、更新、検証、障害対応、ロールバックをこの正本文書へ統合

次の段階から表示名APIと生成辞書を追加しますが、この文書にある境界は維持します。
