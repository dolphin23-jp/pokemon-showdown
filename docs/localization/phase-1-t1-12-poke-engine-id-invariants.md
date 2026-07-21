# Phase 1 T1-12: Rust poke-engine ID boundary invariants

## 目的

T1-12は、foul-playがPythonの対戦状態をRust `poke-engine`へ変換する境界を検査します。日本語表示名はブラウザだけに留め、Rustへ渡るspecies、move、ability、itemの意味がcanonical normalized IDのまま維持されることを確認します。

完了条件は、実戦でRust-backed `State`を取得し、同一個体について次のShowdown形式の正規化IDを確認することです。

```text
species: pikachu
move: thunderbolt
ability: static
item: lightball
```

`poke-engine 0.0.48`のRust enumは同じ値を次の大文字トークンとして直列化します。

```text
PIKACHU
THUNDERBOLT
STATIC
LIGHTBALL
```

T1-12はRustトークンを変更しません。raw Rustトークンをそのまま記録した上で、英数字を小文字化したShowdown形式の比較用IDを別フィールドへ出力します。

## 監査点

固定foul-play `25c976f05cbf2880eaa579afd6db1dcb2c3b57c6`では、境界は次の順序です。

1. `battle_to_poke_engine_state(...)`がPythonから`poke_engine.State`を構築
2. `State.to_string()`で子プロセスへ渡す
3. `PokeEngineState.from_string(state)`でRust-backed `State`を復元
4. `monte_carlo_tree_search(poke_engine_state, ...)`へ渡す

`scripts/patch-foul-play-poke-engine-boundary-log.py`は、3と4の間だけにopt-in監査を追加します。

```text
FOUL_PLAY_POKE_ENGINE_BOUNDARY_LOG=/app/.runtime/poke-engine-boundary.jsonl
```

環境変数がない通常起動ではファイルを開かず、状態変換、MCTS、選択結果を変更しません。

## 記録内容

各JSONLレコードには次を保存します。

- `recorded_at_ns`
- `search_index`
- foul-playが子プロセスへ渡した`serialized_state`
- Rust-backed `State.to_string()`の`rust_state`
- Rust-backed Stateから読み出した`side_one`と`side_two`
- 各Pokemonのraw Rust enumトークン:
  - `rust_id`
  - `rust_ability`
  - `rust_base_ability`
  - `rust_item`
  - `rust_moves`
- 同じトークンから英数字小文字で導出した比較用ID:
  - `id`
  - `ability`
  - `base_ability`
  - `item`
  - `moves`

`serialized_state`と`rust_state`は完全一致を必須とします。比較用IDは監査レポートだけに使用し、MCTSへ渡すStateへ書き戻しません。

## 決定論的単体テスト

`scripts/test-foul-play-poke-engine-boundary-log.py`はPikachuを含む固定状態を生成し、実際に`PokeEngineState.from_string()`で復元してから次を確認します。

- raw Rust enum `PIKACHU` → normalized `pikachu`
- raw Rust enum `THUNDERBOLT` → normalized `thunderbolt`
- raw Rust enum `STATIC` → normalized `static`
- raw Rust enum `LIGHTBALL` → normalized `lightball`
- `State.from_string()`後の完全round-trip
- 日本語文字がない
- 監査が環境変数設定時だけ有効
- 通常runtimeが不変

## 実戦smoke

専用Botチームは`config/bss-engine-boundary-bot.txt`です。先頭個体を次のように固定します。

```text
Pikachu @ Light Ball
Ability: Static
- Thunderbolt
```

`scripts/smoke-bss-poke-engine-boundary-invariants.py`は専用の`EngineBoundaryBot`へchallengeし、team previewで実際に起動したMCTSのRust境界記録だけを検査します。

検査内容:

1. challenger側で日本語サーバー設定を確認
2. 境界ログの開始byte offsetを記録
3. 実戦challengeとteam previewを開始
4. offset以後のRust境界レコードだけを読む
5. `serialized_state == rust_state`を確認
6. 同一Pokemonでraw Rustトークンを保持したまま`pikachu`、`thunderbolt`、`static`、`lightball`へ正規化できることを確認
7. `Pikachu`、`Thunderbolt`、`Static`、`Light Ball`という表示文字列が混入していないことを確認
8. 日本語文字が一つもないことを確認

専用artifact:

```text
bss-poke-engine-boundary-invariant-diagnostics
```

## CI統合

Docker buildでは次を実行します。

- `scripts/patch-foul-play-poke-engine-boundary-log.py`の構文確認
- 固定foul-playへの安全なpatch適用
- patch後ソースの`compile()`検査
- `scripts/test-foul-play-poke-engine-boundary-log.py`
- `config/bss-engine-boundary-bot.txt`のShowdown validator

Render smokeではT1-12専用コンテナを起動します。T1-12の検査後に専用コンテナを削除し、T1-11、T1-10、通常BSS、post-faint回帰は従来の別コンテナで継続します。

## 保護境界

T1-12は次を変更しません。

- `data/`
- `sim/`
- normalized species IDs
- normalized move IDs
- normalized ability IDs
- normalized item IDs
- `|request|`
- `|switch|`
- `|move|`
- `/choose`
- `/team`
- Team Import/Export
- challenge format ID
- client display-name API
- foul-playの通常search結果
- Rust `poke-engine`の入力値

監査ログは境界を観測するだけで、翻訳、逆変換、状態修正には使用しません。比較用の小文字IDも監査JSONLにのみ存在し、Rust Stateや選択処理には戻しません。

## 固定情報

```text
client: 80c72741b52e91d35ee778982a936ea42526c078
client upstream base: 085dfabd9bc53c730ac459edf5c28088677adfc2
foul-play: 25c976f05cbf2880eaa579afd6db1dcb2c3b57c6
poke-engine: 0.0.48
```

T1-12はクライアントSHAを変更しません。

## ロールバック

監査実装に問題がある場合はT1-12のserver squash mergeをrevertし、T1-11時点のruntimeを維持します。テストを通すためにID、protocol、表示名API、foul-play状態、Rust入力を変更してはいけません。
