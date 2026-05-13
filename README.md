# ロケハン3D — Offline 3DGS Viewer

3D Gaussian Splatting (3DGS) ビューワ。**単一の HTML ファイルで完結**する設計で、別途ビルド・サーバ不要。映像作品の事前ロケハン用に作られています。

🌍 **公開デモ**: <https://locahun3d.nakamurakou1108.workers.dev>
🎬 **サンプルシーン**: ページ上の「📥 デモシーンを読み込む」ボタンから、Cloudflare R2 にホストされたサンプル PLY を直接読み込めます(別 URL: [`?demo=1`](https://locahun3d.nakamurakou1108.workers.dev/?demo=1))。

## 主な機能

- `.ply` / `.splat` / `.spz` / `.ksplat` の 3DGS ファイルを直接読み込み
- マウス / WASD / コントローラ / タッチで自由視点
- 距離計測ツール、レイヤ管理、シャドウ、環境光プリセット(朝・昼・夕方・夜)
- カメラショットの記録 + JPEG/4K 書き出し
- 多言語対応(日本語 / 英語)
- iPhone / iPad / Android 含むタッチデバイスにも対応

## 動かし方

`Locahun3D_OfflineViewer.html` をブラウザで直接開くだけ。

```
file:///path/to/Locahun3D_OfflineViewer.html
```

または任意の HTTP サーバから配信:
```
python -m http.server 8000
→ http://localhost:8000/Locahun3D_OfflineViewer.html
```

CDN(jsdelivr)から Three.js + Spark 2.0 + fflate を import するため、初回起動時に**オンライン環境**が必要です(以降はブラウザキャッシュ)。

## 技術スタック

| ライブラリ | バージョン |
|---|---|
| [@sparkjsdev/spark](https://github.com/sparkjsdev/spark) | 2.0.0(3DGS レンダリング) |
| [Three.js](https://threejs.org/) | 0.180.0 |
| [fflate](https://github.com/101arrowz/fflate) | 0.8.2(ZIP 保存) |

## 動作要件

- モダンブラウザ(Chrome 110+ / Edge 110+ / Safari 16+ / Firefox 110+)
- WebGL2 サポート
- 大きな PLY(数百MB〜1GB)を扱う場合は最低 4GB の VRAM を推奨

## 開発用診断ツール

`?diag=1` を URL に付けると、内部メトリクスを 1Hz で記録するサンプラが起動します。さらに以下の sub-flag が使えます:

| URL パラメータ | 効果 |
|---|---|
| `?autoload=path/to/file.ply` | 起動時に自動でファイル読み込み(常時利用可) |
| `&diag=1` | 診断モード起動(以下のフラグの前提) |
| `&rafProbe=1` | 生 rAF コールバック頻度を計測 |
| `&gpuTime=1` | 毎フレーム `gl.finish()` で真の GPU 時間を取得 |
| `&prof=1` | animate() 内のセクション別 CPU プロファイル |
| `&qual=N` | qualScale を N に固定(`0.5` / `0.75` / `1.0` / `1.5`) |
| `&stress=1\|2` | カメラ自動回転(再現可能な負荷テスト) |

`__diag_server.py` を起動してから `http://localhost:8765/Locahun3D_OfflineViewer.html?diag=1` を開くと、サンプルが `__diag.log` に蓄積されます。`__diag_analyze.py` / `__diag_prof.py` などで解析できます。

## 更新確認 (Update Check)

ビューワ右上の **🔄 更新確認** ボタンが GitHub の [`version.json`](./version.json) を直接チェックします。

- ✓ 最新版なら緑表示
- 🔔 新版があれば橙色で点滅、クリックでリリースページ(または `version.json` の `url`)へ遷移
- ⚠ オフラインなら淡色表示

### 新バージョンをリリースするには

1. `Locahun3D_OfflineViewer.html` 内の `CURRENT_VERSION` を新バージョンに更新(例: `0.0.2`)
2. `version.json` の `version` フィールドを新バージョンに更新
3. ついでに `notes` に変更内容を記載
4. `git commit && git push`
5. Cloudflare Workers が自動で再デプロイ(~30秒)
6. 既存ユーザのビューワが次回 `更新確認` ボタンを押した時に検知

`version.json` 形式:
```json
{
  "version": "0.0.2",
  "url": "https://locahun3d.nakamurakou1108.workers.dev",
  "sha256": null,
  "notes": "変更点の要約"
}
```

`sha256` は配布バイナリの SHA-256 ハッシュ(任意)。設定するとビューワが自身のソース(`location.href`)をハッシュしてマッチ確認し、整合性インジケータが点灯します。

セキュリティ: マニフェストの `url` フィールドは **github.com / *.github.io / raw.githubusercontent.com** のみ許可されています(`TRUSTED_UPDATE_HOST_PATTERNS`)。違反すると `RELEASES_FALLBACK_URL` (`github.com/nakamurakou1108/Locahun3D/releases`) に自動フォールバック。

## ライセンス

[Apache License 2.0](./LICENSE) — 商用利用可、改変・再配布自由、特許条項あり。
詳細は LICENSE ファイル参照。
