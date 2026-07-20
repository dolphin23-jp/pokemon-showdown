# Renderへ常設する

この構成では、iPadから固定URLを開くだけでPokemon Showdown、foul-play Bot、構築ライブラリを利用できます。Codespaceの作成、ターミナル操作、`/trn`コマンド入力は不要です。

## 無料枠の注意点

RenderのFree Web Serviceは、HTTPまたはWebSocket通信が15分間ないと休止します。次にURLを開くと自動復帰しますが、通常は約1分の待ち時間があります。Codespacesの環境構築を毎回行うよりは軽いものの、無料枠で完全な常時起動にはなりません。

## 初回だけ行う操作

1. この変更を`master`へマージします。
2. RenderへGitHubアカウントでログインします。
3. **New +** → **Blueprint** を選びます。
4. `dolphin23-jp/pokemon-showdown`を接続します。
5. Renderがルートの`render.yaml`を認識したら、Blueprintを適用します。
6. `ACCESS_TOKEN`を求められたら、自分だけが知っている長いパスワードを入力します。
7. **Apply**を押し、最初のDockerビルドとデプロイの完了を待ちます。
8. 発行された`https://...onrender.com`のURLをiPadのホーム画面またはブックマークへ保存します。

初回ビルドではNode.js、Python、Rust製AIエンジンをまとめて構築するため時間がかかります。二回目以降はイメージキャッシュが利用されます。

## 毎回の使い方

1. 保存したRender URLを開きます。
2. 初回だけ`ACCESS_TOKEN`を入力します。認証Cookieは1年間保存されます。
3. 入口ページの名前欄を確認し、**名前を保存してShowdownを開く**を押します。
4. 次回から名前は自動設定されます。
5. Bot `FoulPlayAI`へ、同じ対戦形式でChallengeします。

## 既定の対戦形式

`[Gen 9] National Dex All Generations BSS`

- 第1～9世代の公式ポケモン、技、持ち物、特性を利用可能
- 第9世代の戦闘仕様
- 禁止級・幻の制限なし
- Species Clauseなし
- Item Clauseなし
- 6体見せ合い、3体選出
- レベル50へ統一
- Botも6体から3体を自動選出
- Botは最大48構築のライブラリから毎試合ランダムに使用

存在しないポケモンや完全な架空データは対象外です。foul-playが未対応のZワザ・ダイマックス依存構築はライブラリ作成時に除外します。

## 名前や強さを変更する

Renderのサービス画面から **Environment** を開きます。

- `DEFAULT_PLAYER_NAME`: 初期表示する自分の名前
- `FOUL_PLAY_USERNAME`: Bot名
- `FOUL_PLAY_SEARCH_TIME_MS`: 通常ターンの探索時間
- `FOUL_PLAY_TEAM_PREVIEW_SEARCH_TIME_MS`: 6体から3体を選ぶ探索時間
- `ALL_GENERATIONS_TEAM_LIMIT`: Bot構築ライブラリの上限

FreeプランはCPUが小さいため、探索時間を大きくすると一手がかなり遅くなります。まず既定値で動作確認してください。

## プライバシー

RenderのWeb Service URL自体は公開URLですが、アプリ全体を`ACCESS_TOKEN`で保護します。Showdown本体の8000番ポートは外部公開せず、同一コンテナ内からだけ接続します。アクセスキーをGitHubへコミットしないでください。
