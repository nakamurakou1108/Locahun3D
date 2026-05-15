# PLY → RAD 変換ツールキット

PLY / SPZ / SOG ファイルを Spark の **RAD 形式** (LoD + チャンクストリーミング対応)
にローカル変換するスクリプト集です。**入力ファイルの隣に `.rad` が出力されます**。

## 使い方は 3 ステップ

### 1. 解凍 → 好きな場所に置く

`ply-to-rad-tools.zip` を解凍。Desktop でも Documents でも、好きなフォルダで OK。

### 2. 初回セットアップ(一度だけ)

#### Windows
`setup.bat` をダブルクリック。

#### macOS / Linux
```bash
chmod +x setup.sh convert.sh
./setup.sh
```

初回は **5〜15 分** かかります(Spark リポジトリのクローン + Rust ビルド)。

### 3. ドラッグ&ドロップで変換

#### Windows

変換したい `.ply` / `.spz` / `.sog` ファイルを **`convert.bat` にドラッグ&ドロップ**。

→ ドロップ元の同じフォルダに `<basename>.rad` が生成されます。

複数ファイルをまとめてドロップしても順次処理されます。

#### macOS / Linux

```bash
./convert.sh path/to/file1.ply
./convert.sh ~/Desktop/scene1.ply ~/Desktop/scene2.ply
```

→ 各ファイルの隣に `.rad` が出力されます。

## 出力例

```
Desktop/
├── my_scene.ply       ← ここにドロップ
└── my_scene.rad       ← 変換後、同じフォルダに出力 (新規生成)
```

## 動作要件

セットアップ実行時に自動チェックされます。不足していれば案内が出ます。

| ツール | 用途 | インストール |
|---|---|---|
| **Node.js 18+** | npm スクリプト実行 | <https://nodejs.org/ja> |
| **Rust(rustup)** | Spark の build-lod は Rust 製 | <https://rustup.rs/> |
| **Git** | Spark リポジトリのクローン | <https://git-scm.com/> |

## 変換時間とサイズの目安

| 元データ | 変換時間 | 出力サイズ |
|---|---|---|
| 100万点群 | 1〜3 秒 | 約 4.5x の膨張 |
| 500万点群 | 約 5 分 | ~250MB(元 58MB) |
| 上限 | 約 3000 万点 | — |

ファイルサイズは膨張しますが、ロケハン3D ビューワーで読み込む際は
**LoD 階層のうち必要な分だけ**取得されるため、実際の表示は元 PLY より遥かに高速です。

## 生成された `.rad` の使い方

### ロケハン3D ビューワーで直接開く(オフライン)

1. ビューワーを開く(`Locahun3D_OfflineViewer.html`)
2. `.rad` ファイルを画面にドラッグ&ドロップ
3. 自動的に LoD ストリーミング再生

### URL 経由で配信(CDN ホスト時)

```
https://locahun3d.nakamurakou1108.workers.dev/?autoload=https://your-cdn.com/scene.rad
```

→ HTTP Range Request チャンクストリーミングで 5 秒以内に初期表示。

## トラブルシューティング

### `setup.bat` で「'cargo' は、内部コマンドまたは外部コマンドとして認識されていません」

Rust が未インストールです。<https://rustup.rs/> から `rustup-init.exe` を実行 →
ターミナル(コマンドプロンプト)を**完全に閉じて再起動**してから `setup.bat` を再実行してください。

### Node.js のバージョンエラー

```bash
node --version
```
で `v18.x.x` 以上が表示されない場合は <https://nodejs.org/ja> から最新 LTS をインストール。

### 変換中に「out of memory」

巨大シーン(> 2000 万点)で発生する可能性があります。
スプラットを分割するか、より大きい RAM を持つマシンで実行してください。

### Spark を最新版に更新したい

```bash
cd spark
git pull
npm install
```

または `setup.bat` / `setup.sh` を再実行すれば自動で `git pull` されます。

### `.rad` が変換後に見つからない

build-lod の出力ファイル名は実装により異なる場合があります。
ドロップ元のフォルダで `*.rad` を手動検索してみてください。
スクリプトは `<basename>-lod.rad` / `<basename>_lod.rad` / `<basename>.rad` の順で探します。

## ライセンス

- 本ツール群(`convert.bat` / `setup.bat` / `convert.sh` / `setup.sh` / README): Apache License 2.0
- Spark 本体(`spark/` 以下、setup.bat 実行で生成): MIT License(World Labs)
- 生成された `.rad` ファイルの権利は元 PLY の著作権者に帰属します

## 関連リンク

- ロケハン3D ビューワー: <https://locahun3d.nakamurakou1108.workers.dev>
- Spark リポジトリ: <https://github.com/sparkjsdev/spark>
- 3Dasset.io(Web 上で同じ変換が可能): <https://3dasset.io/>
- 参考記事(matsutomato): <https://qiita.com/matsutomato/items/c04c5294e40e61571b3c>
