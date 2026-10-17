# TurboBoost Player(ページ内Scratch実行 + 仮想キーボード直結)

iframe は使わず、TurboWarp の実行エンジン(`@turbowarp/scaffolding`)をページ内で動かします。
仮想キーボードは `vm.postIOData('keyboard', {key, isDown})` を直接呼び、DOMのKeyboardEventは生成しません。

## 構成
| ファイル | 役割 |
|---|---|
| `index.html` / `styles.css` | UI(旗・停止・サイズ・全画面・キーボード) |
| `src/player.js` | scaffolding のロードと操作(SB3読込、旗、停止、リサイズ) |
| `src/input-bridge.js` | キー状態管理 → `vm.postIOData` 直送(同時押し・多重保持対応) |
| `src/virtual-keyboard.js` | Pointer Events で押下/解放。cancel・blur・非表示・全画面切替・レイアウト切替で全解放 |
| `src/layouts.js` | 日本語 / English / 記号 の3配列。矢印キーは全配列で逆T字の十字 |
| `src/selftest.js` | 実VMでスプライト座標・変数を読んで判定する自己診断 |
| `tools/make-test-sb3.py` | テストSB3生成 → `test/keytest.sb3` |
| `tools/test-bridge.py` | 偽VMでキー送信ロジックをChromiumで検証(17項目) |

## 起動
```bash
npm run setup          # @turbowarp/scaffolding を取得し vendor/scaffolding/ へコピー(要ネットワーク)
npm run serve          # http://localhost:8080/ を開く(file:// 不可。ES Modules使用のため)
```
GitHub Pages に置く場合は `vendor/scaffolding/` もコミットしてください。

## 動作確認手順
1. `http://localhost:8080/` を開き「テストゲーム」→「▶ 緑の旗」
2. 仮想キーボードの ↑↓←→ を押し続けるとボールが移動、2キー同時押しで斜め移動、離すと停止
3. Space を押すたびに「SPACE x N」の吹き出しが出て、色が変わる
4. 「自己診断」ボタンで上記を自動実行し PASS/FAIL を表示
5. 押したまま指をキー外へ滑らせて離す/ホームに戻る/タブ切替 → キーが残らないこと
6. 日本語・English・記号の各タブで矢印が十字配置であること、全画面でもキーボードが使えること

## 検証状況(正直な報告)
- **実施済み**: `python3 tools/test-bridge.py`(Chromium、偽VM)17項目合格。タッチ複数同時押し、touchCancel、キー外での解放、blur/pagehide/レイアウト切替での解放、3配列の十字配置。
- **未実施**: 実際の TurboWarp VM でのゲーム内動作確認。作業環境にネットワークがなく `@turbowarp/scaffolding` を取得できなかったため、`player.js` の scaffolding API 使用(`Scaffolding.Scaffolding`, `setup/appendTo/loadProject/start/greenFlag/stopAll`, `vm`)と、リサイズ追従、`dist/` 内のファイル名は記憶に基づく想定で、**未検証**です。実機で「自己診断」を実行して確認してください。
- 既存の仮想キーボード実装は参照できていないため、3配列はこちらで再構成したものです(IME切替キーは省略)。既存の配列定義があれば `src/layouts.js` に移植します。
- Scratchが認識するキーは 英数字・Space・矢印・any 中心です。Enter/Shift 等は送信しますがブロックのメニューに無いため通常は無効です。

## トラブルシュート
- 「実行エンジンが見つかりません」: `vendor/scaffolding/` の中身を確認し、全部入りのJS名を `src/player.js` の `CANDIDATES` に追加。
- ステージが縮尺に追従しない: `Player.refreshSize()` の呼び出し先メソッド名を、実際のscaffoldingの公開APIに合わせてください。
- 単一HTMLにしない理由: VM・レンダラ・オーディオが巨大(数MB)でバンドル前提のため、`vendor/` 配置+ES Modules構成にしています。
