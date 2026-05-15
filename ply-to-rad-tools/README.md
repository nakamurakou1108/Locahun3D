# PLY → RAD 変換ツールキット

ロケハン3D ビューワー向けに、PLY / SPZ / SOG ファイルを **RAD 形式**(World Labs / Spark 2.0
のチャンクストリーミング + LoD 形式)へ一括変換するスクリプト集です。

## 何ができる?

- フォルダに置いた `.ply` / `.spz` / `.sog` を **まとめて `.rad` に変換**
- 出力は `output/` フォルダに同名で生成
- 一度セットアップすれば以降ダブルクリックで実行可能(Windows)
- 変換結果は Cloudflare R2 等にアップロードしてストリーミング配信できる

## 必要環境(初回セットアップで自動チェック)

| ツール | 用途 | インストール先 |
|---|---|---|
| **Node.js 18+** | npm スクリプト実行 | <https://nodejs.org/ja> |
| **Rust(rustc + cargo)** | Spark の build-lod は Rust 製 | <https://rustup.rs/> |
| **Git** | Spark リポジトリのクローン | <https://git-scm.com/> |

## 使い方(3 ステップ)

### 1. 初回セットアップ(一度だけ)

#### Windows

エクスプローラで `setup.bat` をダブルクリック。

#### macOS / Linux

ターミナルで:
```bash
chmod +x setup.sh
./setup.sh
```

`spark/` サブフォルダに Spark リポジトリがクローンされ、依存がビルドされます。
初回は 5〜15 分かかります(ネット速度と Rust ビルド時間次第)。

### 2. PLY ファイルを `input/` フォルダに入れる

```
ply-to-rad-tools/
├── input/
│   ├── my_scene_1.ply        ← ここに入れる
│   ├── my_scene_2.ply
│   └── my_scene_3.spz
├── output/                    ← 自動で .rad が生成される
├── spark/                     ← セットアップで作られる
├── convert.bat / convert.sh
└── README.md
```

### 3. 変換実行

#### Windows

`convert.bat` をダブルクリック。

#### macOS / Linux

```bash
./convert.sh
```

完了後、`output/` フォルダに `.rad` ファイルが生成されています。

## 単一ファイルの変換(コマンドライン)

```bash
# Windows
convert.bat path\to\specific.ply

# macOS / Linux
./convert.sh path/to/specific.ply
```

## 出力ファイルの活用

生成された `.rad` を:

1. **Cloudflare R2 / S3 等の CDN にアップロード**
2. **ロケハン3D ビューワーに URL 渡し**:
   ```
   https://locahun3d.nakamurakou1108.workers.dev/?autoload=https://your-cdn.com/scene.rad
   ```
3. → HTTP Range Request で**段階的にストリーミング読込**、初期表示 5 秒以内

## 変換時間とファイルサイズの目安

| 元データ | 変換時間 | 出力サイズ |
|---|---|---|
| 100万点群 | 1〜3 秒(公式)| 約 4.5x の膨張 |
| 500万点群 | 約 5 分(実測) | ~250MB(元 58MB SOG)|
| 上限 | 約 3000 万点 | — |

サイズは膨張しますが、配信時は**必要な LoD レベルのみ**を取得するため、
ユーザーの初期ダウンロード量は元 PLY より遥かに少なくなります。

## トラブルシューティング

### `setup.bat` で「'cargo' は、内部コマンドまたは外部コマンド...として認識されていません」

→ Rust が未インストール、または PATH に追加されていません。
<https://rustup.rs/> から `rustup-init.exe` を実行し、再ログイン or 再起動してください。

### Node.js のバージョンエラー

```bash
node --version
```
で `v18.x.x` 以上が出ない場合は <https://nodejs.org/ja> から最新 LTS をインストール。

### 変換中に「out of memory」

巨大シーン(>2000 万点)の場合、PC の RAM 不足の可能性があります。
スプラットを分割するか、より大きい RAM を持つマシンで実行してください。

### Spark を更新したい

```bash
cd spark
git pull
npm install
```

## ライセンス

- 本ツール群(`convert.bat` / `setup.bat` / `convert.sh` / `setup.sh` / README): Apache License 2.0
- Spark 本体(`spark/` 以下): MIT License(World Labs)
- 生成された `.rad` ファイルの権利は元 PLY の著作権者に帰属

## 関連リンク

- ロケハン3D ビューワー: <https://locahun3d.nakamurakou1108.workers.dev>
- Spark リポジトリ: <https://github.com/sparkjsdev/spark>
- 3Dasset.io(Web 上で同じ変換が可能): <https://3dasset.io/>
- 参考記事(matsutomato): <https://qiita.com/matsutomato/items/c04c5294e40e61571b3c>
