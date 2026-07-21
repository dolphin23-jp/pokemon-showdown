# Phase 1 T1-13: integration regression

## 目的

T1-13はPhase 1の最終統合回帰です。新しい表示機能やruntime処理は追加せず、T1-00からT1-12までに構築した日本語表示、固定クライアント、サーバープロトコル、foul-play入力、Rust `poke-engine`境界、通常対戦、ブラウザ配信をクリーン環境で再検証します。

過去計画で定義された完了条件は次です。

```text
Dockerをクリーンビルドして全テスト・ブラウザ確認・成果物監査
全条件成功
Phase 2へ進める最終報告を作成
```

## 変更範囲

T1-13はテスト・文書・成果物監査だけを変更します。

- `scripts/audit-phase1-integration.py`
- `scripts/wait-phase1-workflows.py`
- `.github/workflows/phase1-integration-regression.yml`
- `.github/workflows/render-smoke.yml`の日本語フォント準備
- `scripts/check-phase1-baseline.py`
- `scripts/check-localization-docs.py`
- `docs/localization/README.md`
- この文書
- `Dockerfile`のPython構文検査対象

Render smokeの検査内容と成果物経路は維持します。日本語フォント準備だけは、既存フォントがあれば即時通過し、未導入時はapt通信を時間制限付きで最大3回試行し、最後に日本語フォントの存在を検証する形へ堅牢化します。ゲームデータ、シミュレーター、クライアント実装、翻訳データ、foul-playの対戦判断、Rust Stateは変更しません。

## workflow分離

T1-13は、既存の検証経路を重複・改変しないため二段構成にします。

### 証拠生成

既存の`Render smoke test`が次を同一runで実行します。

1. Phase 1 T1-13基準状態を記録
2. 固定クライアントforkと完全SHAをGitHub上で検証
3. Docker imageを通常の`docker build`でクリーン構築
4. Docker build内の構文、文書、launcher、foul-play patch、単体テスト、team validationを実行
5. 埋め込み固定クライアントとbuild manifestを検証
6. T1-10の複製入力fixtureを実行
7. T1-12専用コンテナでRust AI境界のIDを実戦検証
8. 通常コンテナでT1-11のfoul-play受信データを実戦検証
9. T1-10の生WebSocket protocolを実戦検証
10. BSS対戦がturn 1へ到達することを確認
11. 瀕死後の強制交代と継続を確認
12. access gateと固定ローカルクライアント配信を確認
13. 外部`play.pokemonshowdown.com`を名前解決不能にしてブラウザ表示を確認
14. 1024×1366のlauncher/client PNGを取得
15. ログ、status、JSON、HTML、headers、JavaScript、PNGをartifactとして保存

### 最終判定

専用の`Phase 1 integration regression` workflowが同一head SHAについて次を行います。

1. `scripts/wait-phase1-workflows.py`で以下を待つ
   - `Localization documentation`
   - `Node.js CI`
   - `Render smoke test`
2. 3 workflowがすべて`success`であることを要求
3. 成功した`Render smoke test`のrun IDを固定
4. そのrunのartifactを`actions/download-artifact`で全取得
5. `merge-multiple: true`で一つの監査ディレクトリへ展開
6. `scripts/audit-phase1-integration.py`で成果物を監査
7. `ready_for_phase2: true`を要求
8. 最終レポートを専用artifactとして保存

別commitや過去runのartifactは使用しません。

## 全テスト

T1-13で継続成功を要求する検査は次です。

### Docker build内

- Node.js lintと構文検査
- launcher日本語設定テスト
- 固定クライアント配信テスト
- Python構文検査
- 日本語化文書・契約検査
- foul-playローカルログインテスト
- foul-play battle fallbackテスト
- foul-play raw receive記録テスト
- Rust `poke-engine`境界記録テスト
- BSS team validation
- T1-10複製入力fixture
- 固定クライアントbuild manifest検証

### 実戦smoke

- T1-12 Rust AI境界のIDテスト
- T1-11 foul-play受信ログ不変テスト
- T1-10サーバープロトコル不変テスト
- 通常BSSのturn 1到達
- 瀕死後の強制交代

### ブラウザ・配信

- 未認証アクセスは401
- access token後にlauncherを取得
- `/client.html`は`pinned-local`
- `/showdown`は同一オリジン接続
- named login後の日本語設定bootstrap
- client JavaScriptはimmutable cache
- path traversalと未知resourceは404
- 外部Showdown clientへ依存しない
- launcherとclientを1024×1366で撮影
- 日本語フォント準備は既存フォントを優先し、apt使用時は各コマンド3分上限・最大3回で終了する

## 成果物監査

`scripts/audit-phase1-integration.py`はダウンロードしたRender smoke成果物を読み、以下を検査します。

### exit status

すべて`0`であることを要求します。

- `docker-build.status`
- `bss-poke-engine-boundary-invariants.status`
- `bss-foul-play-input-invariants.status`
- `bss-protocol-invariants.status`
- `bss-smoke.status`
- `bss-faint-smoke.status`

### 機械可読レポート

- `phase1-baseline.json`
- `client-pin.json`
- `client-build-verification.json`
- `client-build-manifest.json`
- `protocol-render-invariants.json`
- `poke-engine-boundary-report.json`
- T1-11とT1-10のsmokeログ内JSON

### ブラウザ証拠

- 認証済みlauncher HTML
- 認証済みclient HTMLとheaders
- client-main/configのheadersとcontent
- local-client alias
- 404応答
- 非保護baseline HTML
- launcher/client PNG

PNGはsignatureとIHDRを読み、両方が正確に`1024 × 1366`であることを要求します。

### manifest

全必須成果物について次を最終レポートへ保存します。

- byte size
- SHA-256

HTTP statusで404を検証済みの`client-traversal.txt`だけは空本文を許容します。空の場合もSHA-256を記録します。

## 最終レポート

生成ファイル:

```text
/tmp/phase1-integration-regression.json
```

専用GitHub Actions artifact:

```text
phase1-integration-regression-report
```

artifactには次を含めます。

- `phase1-integration-regression.json`
- `phase1-workflow-runs.json`

後者には監査対象となった3 workflowのrun ID、status、conclusion、head SHAを保存します。

完了時の必須値:

```json
{
  "phase": "Phase 1",
  "task": "T1-13",
  "phase1_complete": true,
  "ready_for_phase2": true
}
```

`ready_for_phase2`は、3 workflow、Docker build、全回帰、固定クライアント、ブラウザ、iPad PNG、成果物manifest、保護境界の全条件が成功した場合だけ`true`になります。監査スクリプトは条件不足時に非0で終了し、レポートを成功扱いしません。

## 保護境界

T1-13で変更・翻訳してはいけないもの:

- `data/`
- `sim/`
- species ID
- move ID
- ability ID
- item ID
- `|request|`
- `|switch|`
- `|move|`
- `/choose`
- `/team`
- Team Import/Export
- challenge format ID
- foul-playが受け取る名前・ID・状態
- Rust `poke-engine`へ渡すState
- `window.PSDisplayNames`の表示専用契約

固定クライアントSHA:

```text
80c72741b52e91d35ee778982a936ea42526c078
```

## CIでの成功条件

- Localization documentation: success
- Node.js CI: success
- Render smoke test: success
- Phase 1 integration regression: success
- `Audit Phase 1 integration artifacts`: success
- `Require Phase 1 ready for Phase 2`: success
- `phase1-integration-regression-report`が生成される

## 障害時の原則

監査に失敗した場合、statusやレポートを書き換えて成功扱いにしてはいけません。失敗した元テスト、配信経路、成果物生成を修正し、Docker clean buildから全統合回帰を再実行します。

T1-13自体はruntime機能を持たないため、ロールバックはT1-13の監査・文書変更をrevertし、T1-12時点の動作を維持します。

## Phase 1完了

4つのCIがすべて成功し、最終レポートが`ready_for_phase2: true`を示した時点でPhase 1を完了とします。Phase 2の具体的タスクは別の計画で定義し、T1-13から推測して開始しません。
