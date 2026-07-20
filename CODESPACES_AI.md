# iPad + GitHub Codespacesでfoul-playと対戦する

このリポジトリは、Pokemon Showdownサーバー、foul-play Bot、ブラウザ用クライアント中継を同じCodespace内で起動する構成です。通常はコマンド入力を必要としません。

## 初回起動

1. このリポジトリからCodespaceを作成します。
2. 既存のCodespaceでこの設定を取り込んだ場合は、`git pull` のあと `bash scripts/showdown-ai.sh restart` を実行します。
3. 初回だけNode.jsとPythonの依存関係、およびRust製の探索エンジンをインストールします。
4. セットアップ後、Showdownサーバー、foul-play、入口ページ兼クライアント中継が自動起動します。
5. ブラウザで入口ページが開かなければ、VS Codeの **PORTS** タブからポート `3000` の地球アイコンを押します。
6. 入口ページの **構築ライブラリを開く** から自分用の構築をコピーします。
7. ShowdownのTeambuilderで `[Gen 9] BSS Reg I` の新規チームを作り、Import/Exportへ貼り付けます。
8. 入口ページに表示されたBot名へ `gen9bssregi` で対戦を申し込みます。
9. 6体見せ合い後に3体を選出します。Bot側も自動で3体を選びます。

## Regulation I構築ライブラリ

既定モードはScarlet/Violetの `[Gen 9] BSS Reg I` です。Smogonの公式 **Battle Stadium Singles Sample Teams** に掲載されたRegulation I構築を、Pokemon ShowdownのTeams APIから取得・検証して利用します。

- 現在の登録数: 9構築
- Bot側: 対戦ごとに9構築からランダム選択
- 人間側: 入口ページの構築ライブラリからワンタップでコピー
- 更新: 起動時に不足分を取得。手動更新は `bash scripts/showdown-ai.sh refresh-teams`

構築のID・タイトル・作成者は `config/bss-team-sources.tsv` で管理します。新しいサンプル構築を追加したい場合は、Pokemon Showdown Teamsのteam IDを同ファイルへ追加します。

## モード切り替え

BSS Reg Iへ切り替える:

```bash
bash scripts/showdown-ai.sh mode bss
```

従来のGen 9 Random Battleへ戻す:

```bash
bash scripts/showdown-ai.sh mode random
```

どちらもBotと入口ページを自動で再起動します。

## 通信構成

ブラウザはPrivateの3000番ポートだけへ接続します。3000番のNode.jsプロキシが、公式Showdownクライアントの静的ファイルと、Codespace内部の8000番ShowdownサーバーへのHTTP/WebSocket通信を中継します。

そのため、8000番ポートをPublicにする必要はありません。8000番はPrivateのまま利用します。

## VS Codeのタスク

コマンドパレットから **Tasks: Run Task** を開くと、次を選択できます。

- `Showdown AI: Start`
- `Showdown AI: Stop`
- `Showdown AI: Restart`
- `Showdown AI: Status`
- `Showdown AI: Logs`
- `Showdown AI: Use BSS Reg I`
- `Showdown AI: Use Random Battle`
- `Showdown AI: Refresh BSS Teams`

## Botの強さを調整する

Codespacesの環境変数またはSecretsで次を設定し、`Showdown AI: Restart` を実行します。

| 変数 | 既定値 | 意味 |
| --- | ---: | --- |
| `FOUL_PLAY_FORMAT` | 保存モード。初期値 `gen9bssregi` | 対戦形式を直接固定する場合に設定 |
| `FOUL_PLAY_TEAM_NAME` | 自動生成ライブラリ | Botが使うチームファイルまたはフォルダ。通常は未設定のままでよい |
| `FOUL_PLAY_SEARCH_TIME_MS` | `500` | 通常ターンの1状態あたり探索時間 |
| `FOUL_PLAY_TEAM_PREVIEW_SEARCH_TIME_MS` | `1000` | 6体から3体を選ぶ際の探索時間 |
| `FOUL_PLAY_SEARCH_PARALLELISM` | `1` | 通常ターンの並列探索数 |
| `FOUL_PLAY_TEAM_PREVIEW_SEARCH_PARALLELISM` | `1` | 選出時の並列探索数 |
| `FOUL_PLAY_SEARCH_THREADS` | `1` | 各探索で使うスレッド数 |
| `FOUL_PLAY_USERNAME` | 自動生成 | Botの表示名 |
| `FOUL_PLAY_PASSWORD` | 未設定 | 登録済みBotアカウントを使う場合のみ設定 |

2コアのCodespaceでは、まず既定値で動作確認してください。通常ターンの探索時間を上げる場合は `750`〜`1000`、選出時間は `1500` 前後から試すのが安全です。

## セキュリティ

入口とクライアントはCodespacesのPrivateな3000番ポートで提供されます。Showdown本体の8000番ポートは外部公開しません。Codespaceを他人へ共有していない限り、従来のPublicポート構成より安全です。

## トラブル時

まず `Showdown AI: Logs` を実行します。手動コマンドは次のとおりです。

```bash
bash scripts/showdown-ai.sh status
bash scripts/showdown-ai.sh logs
bash scripts/showdown-ai.sh restart
bash scripts/showdown-ai.sh refresh-teams
```

Python環境やサブモジュールが壊れた場合は、次を再実行します。

```bash
bash scripts/codespaces-setup.sh
```
