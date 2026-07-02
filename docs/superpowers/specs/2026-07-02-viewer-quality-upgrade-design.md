# ビューアー画質アップ設計 — FHDキャプチャ＋RAD LOD改善

- 日付: 2026-07-02
- ステータス: 承認済み（ユーザー承認: アプローチ=1A+2A→実測→2B判断、設計S1〜S5承認）
- 対象repo: `F:\Htlml\3DGS\Locahun3D`（src/断片編集 → `node build.mjs` → 単一HTML）
- 大原則: **既存の操作・UI・低/中ティア挙動・PLY/SPLAT経路は一切変更しない**

## 背景と問題

1. **JPEG撮影がぼやける**: 現行の `captureCamShot` は「ライブ画面のカメラ枠部分を切り出して目標解像度へ拡大コピー」する方式。枠が画面上で小さいと実ソースピクセルが1920幅に届かず、拡大＝ぼやけ。
2. **RADが荒い/回転で2-3秒ラグ**:
   - 荒さ: `lodScale` を2.0以上に上げても splat総予算 `lodSplatCount`（desktop既定250万）に当たって飽和していた。両方上げないと広範囲精細化しない。
   - ラグ: RADのLODツリーは「親チャンク到着後にのみ子の存在が判明する」直列ウォーク。深さ1段ごとに1RTTが直列加算され、さらにSpark内部のdecodeワーカープールが**4スレッド固定（ハードコード）**のため、ビューア設定済みの `numLodFetchers=12` は実効頭打ち。

## 採用アプローチ（承認済み）

**段階戦略**: 1A（PRブーストキャプチャ）＋2A（公式プロパティのみのLOD改善）を実装 → 実測 → 0.5秒未達なら2B（ワーカープールパッチ版Spark自家ホスト）を別途提案。

却下案: renderer.setSize一時変更（過去に黒帯実害）、WebGLRenderTarget独立レンダー（同族リスク・スパイク要）、最初から2B（フォーク管理コスト前倒し）。

## S1. FHDキャプチャ = 一時pixelRatioブースト

変更箇所: `src/js/114_capture_render.js` の `captureCamShot` 内に閉じる。

1. `target = _camTargetResolution()`（既存。16:9=1920×1080、4Kトグルで2倍）
2. `needPR = target.w / fr.w`（fr=`_camFrameRect()`のCSS幅）
3. `boostPR = clamp(needPR, 現PR, 上限)`
   - 上限: desktop **4.0** / mobile 既存スーパサンプル上限（`devicePixelRatio×2.2`）
   - 追加クランプ: `キャンバスCSS幅×boostPR ≤ 16384`（WebGL最大バッファ寸法）
4. `boostPR > 現PR` のときだけ `renderer.setPixelRatio(boostPR)` → 既存の「2回レンダー＋90msソート待ち」→ 切り出し（**ソース座標のPRは boost後の値で再計算**）→ **finally相当で確実にPR復元**（復元式 `min(devicePixelRatio,_PR_CAP)*qualScale` は既存 114:192-194 を流用。カメラツール中は `_applyRenderPixelRatio()` で望遠ブーストへ戻す）
5. needPR≤現PR なら何もしない（現挙動と完全一致）

不変: HUD/パネル/ビネット/sunViz隠し、グリッド焼込（`cam.includeGrid`→`_drawGridOnCanvas`）、撮影後の全復元。

安全根拠: pixelRatio一時引き上げは望遠スーパサンプル（`030_renderer_scene.js:53-66`、2026-06-27〜）で実証済みの機構。`renderer.setSize` は使わない（黒帯バグの経路）。

## S2. 高画質時のLOD範囲拡大（画質ボタン「高」のみ発動）

変更箇所: `src/js/410_ui_controls.js` の `setQuality`、`src/js/180_splat_decimation_user_toggled_low_poly_m.js` のティア表。

「高」(qualIdx=2) 選択時、RAD(paged)シーン限定で:

| プロパティ | desktop | laptop_ok | tablet/phone |
|---|---|---|---|
| `sparkRenderer.lodSplatCount` | 250万→**500万** | →300万 | **据え置き** |
| `lodScale` 高ティア | 2.2→**3.0** | 1.6→2.0 | 据え置き |

- 低/中へ戻したら既定値へ復帰（lodSplatCountは`undefined`に戻して端末別既定に委ねる）
- 両プロパティともSparkが変更を検知して`lodDirty`を立てるためライブ反映・再ロード不要（SparkRenderer.ts:1160-1163, 1194-1201）
- `maxPagedSplats`（VRAMプール、desktop 1677万）は触らない
- 初期値は上表、S4の実測で微調整可

## S3. 回転ラグ短縮（公式プロパティのみ）

新規断片 `src/js/293_rad_lod_prefetch.js`（`src/template.html` にinclude行を追加）:

1. **全方位プリウォーム**: RADロード完了後、`sparkRenderer.lodQuatOverride` に12方位×短dwell（フェッチ待ち行列が空くまで or 上限~500ms/方位）を順に設定して一周 → 周囲チャンクをページプール(LRU, desktop 1677万splat)へ常駐化。**一度読んだ方向への回転はほぼ0秒化**。
   - desktopのみ（mobileは帯域/従量配慮でスキップ）
   - ユーザー入力（回転/移動）検知で即中断、アイドル1秒で再開、1周完了で終了
   - シーン破棄（レイヤー削除/差し替え）で停止
2. **回転先読み**: 慣性回転中（`yaw≠_yawTarget` 等）は目標方向のクォータニオンを `lodQuatOverride` に先出し → 到達前にフェッチ開始。静止で `null` に戻す。
3. **安全規則**: JPEG撮影・録画中は override 強制 `null`（実カメラのLODを最優先）。walk mode 中はプリウォーム無効。
4. **配信RTT**: 本番（viewer.locahun3d.com→R2）のチャンクフェッチ時間を実測。有意なら `/api/demo-asset/` WorkerへのCFエッジキャッシュ追加を別コミットで検討（本設計のスコープ外、報告のみ）。

## S4. 計測と合格基準

- `?diag=1` の `__diagState` に rotate-to-sharp 計測を追加: 回転（lodDirty相当のビュー変化）→ pager のフェッチ待ち行列が空になるまでの時間、＋pager統計（待ち行列長/実行中フェッチ数）を露出
- 本番デモRAD＋実Chrome（Chrome MCP）で90°ヨージャンプをスクリプト計測
- **合格基準: 未訪問方向 p50 ≤0.5s／既訪問（プリウォーム済み）方向 ≈0s**
- 未達の場合: 2B（Spark `SplatWorker.ts:100` `maxWorkers=4`→8 パッチ版を viewer.locahun3d.com に自家ホストし importmap 差し替え）を提案として起票。本設計では実装しない
- 非回帰: 低/中ティアのFPSウォッチドッグ挙動、録画（枠クロップFHD）、ZIP保存/復元、AR、モバイルスモーク。**スクショ目視検証必須**（キャプチャ前後比較を含む）

## S5. 変更範囲と不変条件

| ファイル | 変更 |
|---|---|
| `src/js/114_capture_render.js` | S1 PRブースト＋復元 |
| `src/js/410_ui_controls.js` | S2 「高」時の lodSplatCount/lodScale 切替 |
| `src/js/180_splat_decimation_user_toggled_low_poly_m.js` | S2 ティア表拡張 |
| `src/js/293_rad_lod_prefetch.js`（新規） | S3 プリウォーム＋先読み |
| `src/template.html` | 293 のinclude行追加 |
| `src/js/292_demo_scene_showcase.js` or 293 | S4 diag計測（?diag=1限定） |

不変条件: UI要素・操作・既定の低/中ティア挙動・PLY/SPLAT経路・録画/ZIP/AR。各機能（S1/S2/S3）は独立に revert 可能な粒度でコミットする。

## エラー処理

- S1: try/finally でPR復元を保証（例外時も画面解像度が壊れない）
- S3: override の所有者は293断片のみとし、キャプチャ/録画開始フックで無条件 null 化。多重発動防止（1シーン1周）
- S2: sparkRenderer 未生成（PLYのみ等）や lodSplatCount 非対応ビルドでは silent no-op

## 付録: 調査で確定したSpark 2.0.0内部事実（実装者向け・再調査不要）

検証対象: GitHub `sparkjsdev/spark` tag v2.0.0 (commit ea56ee7) = CDN dist（importmapピン先）と一致確認済み。

- **LOD選択**: `pixelScaleLimit = 2·tan(fov/2)/renderSize.y × lodRenderScale`（SparkRenderer.ts:1132-1146）。renderSize は `renderer.setSize` 由来で **pixelRatioは選択に入らない**（→S1のPRブーストはラスタ解像度のみ向上、LOD選択は不変。これで十分＝LOD側はS2/S3が担当）
- **予算**: `maxSplats = (lodSplatCount ?? 端末別既定[desktop 250万]) × lodSplatScale`（1128-1130）。ページプールは別枠 `maxPagedSplats`（desktop 256page×65536=1677万、LRU退避）
- **更新トリガ**: `lodDirty` フラグ駆動。視点の移動1m/回転(quat dot 0.01)で発火（1167-1174）。`lodScale`/`maxSplats`/`pixelScaleLimit` 変化でも発火（1160-1163, 1194-1201）→ライブ変更可
- **ラグの正体**: 親チャンク到着→decode→木更新→`lodDirty`再点火→子チャンク要求、の反復カスケード（1289-1290, 1479-1491）。深さ×RTTが直列。decodeワーカー `maxWorkers=4` ハードコード（SplatWorker.ts:100）のため `numLodFetchers>4` はdecode側で頭打ち
- **公式ノブ**: `lodSplatCount`/`lodSplatScale`/`lodRenderScale`/`numLodFetchers`/`maxPagedSplats`（SparkRendererコンストラクタ、ビューアは 030_renderer_scene.js:84 で構築済み）、`mesh.lodScale`（実行時可変）、`sparkRenderer.lodPosOverride`/`lodQuatOverride`（LOD選択視点の強制、1152-1157）、`pager.fetchPriority`（公開配列）
- **使用禁止/注意**: `coneFoveate:0` はRADでdegenerate（1splat化）→ビューアは既にRADでfoveation系オプションをdelete済み（Spark既定復帰）。`setPrefetchCameras` はv2.0.0でコメントアウト無効
- 実測カーブ（ビューア既存メモ）: lodScale 0.5→65万 / 1.0→164万 / 1.4→239万 / **2.0以上→~250万で飽和（＝予算頭打ちの証拠）**

## 実測済みの現行値（参考）

- 画質ティア: `qualScale=[0.75,1.0,1.5]`、RAD `lodScale` 表 desktop[0.8/1.5/2.2] laptop[0.7/1.1/1.6] tablet[0.5/0.8/1.2] phone[0.45/0.7/1.0]（180:61-70）
- `numLodFetchers`: desktop 12 / mobile 6（030:83-84）
- 録画: `_camTargetResolution()` でFHD枠クロップ済み（113b:537-566）— 静止画をこれに揃えるのが本設計
