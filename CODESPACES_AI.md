# iPad + GitHub Codespacesでfoul-playと対戦する

固定URLから利用する場合は、CodespacesよりRender版が簡単です。初回設定は [`RENDER_DEPLOY.md`](RENDER_DEPLOY.md) を参照してください。この文書は開発・トラブル対応用のCodespaces手順です。

## 初回起動

1. このリポジトリからCodespaceを作成します。
2. 既存のCodespaceで変更を取り込む場合は、`git pull` のあと `bash scripts/showdown-ai.sh restart` を実行します。
3. 初回だけNode.js、Python、Rust製探索エンジンをインストールします。
4. ブラウザで入口ページが開かなければ、VS Codeの **PORTS** タブからポート`3000`を開きます。
5. 入口ページへ自分の名前を入力してShowdownを開きます。名前はブラウザへ保存され、次回から自動設定されます。
6. 構築ライブラリから構築をコピーし、TeambuilderのImport/Exportへ貼り付けます。
7. Botへ同じ形式でChallengeします。

## 既定形式: All Generations BSS

`[Gen 9] National Dex All Generations BSS`

- 全世代の公式ポケモン・技・持ち物・特性
- 第9世代の戦闘仕様
- 禁止級・幻の制限なし
- Species Clauseなし
- Item Clauseなし
- 6体見せ合い、3体選出
- レベル50へ統一
- Botも自動で3体を選出
- 最大48構築から毎試合ランダム選択

公開されたNational Dex構築を取得し、独自形式で再検証してライブラリを作ります。foul-playが未対応のZワザ・ダイマックス依存構築は除外します。公開APIが利用できない場合も、リポジトリ内の全世代向け構築をフォールバックとして利用します。

## モード切り替え

```bash
# 全世代・制限ほぼなし・6→3
bash scripts/showdown-ai.sh mode all

# 実機Regulation I準拠
bash scripts/showdown-ai.sh mode bss

# 従来のランダムバトル
bash scripts/showdown-ai.sh mode random
```

いずれもBotと入口ページを自動で再起動します。

## 通信構成

ブラウザはPrivateの3000番ポートだけへ接続します。3000番のNode.jsプロキシが、公式Showdownクライアントの静的ファイルと、Codespace内部の8000番ShowdownサーバーへのHTTP/WebSocket通信を中継します。8000番をPublicにする必要はありません。

## VS Codeのタスク

コマンドパレットから **Tasks: Run Task** を開くと、起動・停止・ログ確認・各モードへの切り替え・構築ライブラリ更新を選択できます。

## Botの強さを調整する

| 変数 | 既定値 | 意味 |
| --- | ---: | --- |
| `FOUL_PLAY_FORMAT` | 保存モード。初期値`gen9nationaldexallgenerationsbss` | 対戦形式を固定 |
| `FOUL_PLAY_TEAM_NAME` | 自動生成ライブラリ | Botが使う構築ファイルまたはフォルダ |
| `FOUL_PLAY_SEARCH_TIME_MS` | `500` | 通常ターンの探索時間 |
| `FOUL_PLAY_TEAM_PREVIEW_SEARCH_TIME_MS` | `1000` | 6体から3体を選ぶ探索時間 |
| `FOUL_PLAY_SEARCH_PARALLELISM` | `1` | 通常ターンの並列探索数 |
| `FOUL_PLAY_TEAM_PREVIEW_SEARCH_PARALLELISM` | `1` | 選出時の並列探索数 |
| `FOUL_PLAY_SEARCH_THREADS` | `1` | 各探索で使うスレッド数 |
| `FOUL_PLAY_USERNAME` | 自動生成 | Bot名 |
| `DEFAULT_PLAYER_NAME` | `Dolphin23` | 入口ページの初期プレイヤー名 |
| `ALL_GENERATIONS_TEAM_LIMIT` | `48` | 全世代構築ライブラリの上限 |

## トラブル時

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
