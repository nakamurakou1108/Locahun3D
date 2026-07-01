# ビューアー モジュール分割（純粋連結）実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 22,680行超の単一HTMLビューアーを、意味を1バイトも変えずにセクション単位のソースファイル群＋連結ビルドへ分割する。

**Architecture:** 元HTMLを行範囲リスト(cuts.json)で機械的に切り出して `src/` を生成し、`build.mjs` が `{{include:...}}` プレースホルダへ逆連結して単一HTMLを再構成する。合格条件は **ビルド出力と元ファイルのSHA-256一致**。spec: `docs/superpowers/specs/2026-07-02-viewer-module-split-design.md`

**Tech Stack:** Node.js単体（npm依存ゼロ）。ES modules (.mjs)。

**運用上の注意（実行中ずっと有効）:**
- 移行中は正本 `Locahun3D_OfflineViewer.html` への機能修正を凍結する。もし緊急修正が入ったら Task 5 の cuts.json 生成からやり直す（行番号がズレるため）
- すべてバイト処理。テキストモードでの読み書き・EOL変換は厳禁（ファイルはLF）。Nodeでは `latin1` エンコーディングで読み書きするとバイト列が1:1で保存される — 各スクリプトはこの方式で統一する
- 作業リポジトリ: `F:\Htlml\3DGS\Locahun3D\`（Task 1 で作成）。Dropbox側 (`F:\UNDEFINED Dropbox\UNDEFINED\Works\MFF\01_ProjectFile\3DGS\`) はTask 1以降触らない

---

### Task 1: リポジトリ再クローンと現状整合チェック

**Files:**
- Create: `F:\Htlml\3DGS\Locahun3D\`（git clone）

- [ ] **Step 1: clone**

```bash
cd /f/Htlml/3DGS && git clone https://github.com/Locahun3D/Locahun3D.git Locahun3D
```

- [ ] **Step 2: HEADがDropbox側と一致することを確認**

```bash
cd /f/Htlml/3DGS/Locahun3D && git rev-parse HEAD
cd "/f/UNDEFINED Dropbox/UNDEFINED/Works/MFF/01_ProjectFile/3DGS" && git rev-parse HEAD && git status --short
```
Expected: 同一ハッシュ。違う場合はDropbox側に未pushコミットがある → Dropbox側で `git push` してからclone側で `git pull`。
`git status --short` に正本HTML・deploy-viewer.sh・index.html等の**未コミット変更が出たら停止してユーザーに報告**（コミットするか破棄するかの判断を仰ぐ。2026-07-01時点で deploy-viewer.sh / index.html / ply-to-rad-tools / favicon群に未コミット変更が存在することが分かっている）。

- [ ] **Step 3: 正本HTMLのSHAがclone側とDropbox側で一致することを確認（巻き戻り検知）**

```bash
sha256sum /f/Htlml/3DGS/Locahun3D/Locahun3D_OfflineViewer.html "/f/UNDEFINED Dropbox/UNDEFINED/Works/MFF/01_ProjectFile/3DGS/Locahun3D_OfflineViewer.html"
```
Expected: 同一。**不一致なら停止してユーザーに報告**（Dropbox巻き戻りの可能性。2026-06-28の事故参照）。

- [ ] **Step 4: 基準SHAを記録**

```bash
cd /f/Htlml/3DGS/Locahun3D && sha256sum Locahun3D_OfflineViewer.html | tee /tmp/baseline.sha
wc -l Locahun3D_OfflineViewer.html
```
以後の全タスクでこのSHAを「元ファイルSHA」と呼ぶ。

---

### Task 2: 抽出スクリプト tools/split/extract.mjs（フィクスチャ検証つき）

**Files:**
- Create: `tools/split/extract.mjs`
- Create: `tools/split/fixtures/mini.html`
- Create: `tools/split/fixtures/mini-cuts.json`

- [ ] **Step 1: フィクスチャを書く（先に期待動作を固定）**

`tools/split/fixtures/mini.html`（LFで保存、最終行も改行で終える）:
```html
<!doctype html>
<style>
body{margin:0}
</style>
<script>
const a = 1;
const b = 2;
</script>
```

`tools/split/fixtures/mini-cuts.json`:
```json
[
  { "out": "template", "start": 1, "end": 2 },
  { "out": "src/css/010_main.css", "start": 3, "end": 3 },
  { "out": "template", "start": 4, "end": 5 },
  { "out": "src/js/010_a.js", "start": 6, "end": 7 },
  { "out": "template", "start": 8, "end": 8 }
]
```

- [ ] **Step 2: extract.mjs を実装**

`tools/split/extract.mjs`:
```js
// 元HTMLを cuts.json の行範囲どおりに src/ へ機械分割する使い捨てツール。
// 使い方: node tools/split/extract.mjs <original.html> <cuts.json> <outdir>
// cuts.json: [{ out, start, end }] 1始まり・両端含む行番号。
//   out が "template" の範囲は src/template.html に原文のまま残り、
//   それ以外は out のパスへ書き出され、template には {{include:out}} 行が入る。
// 検証: 範囲が元ファイル全行を隙間なく・重複なく・昇順に被覆しない限り何も書かない。
import fs from 'node:fs';
import path from 'node:path';

const [, , origPath, cutsPath, outDir] = process.argv;
if (!origPath || !cutsPath || !outDir) {
  console.error('usage: node extract.mjs <original.html> <cuts.json> <outdir>');
  process.exit(1);
}

// latin1 = バイト1:1のまま文字列化（EOL変換なし）
const orig = fs.readFileSync(origPath, 'latin1');
if (!orig.endsWith('\n')) { console.error('FATAL: original must end with \\n'); process.exit(1); }
const lines = orig.split('\n');           // 末尾\nのため最終要素は空文字
lines.pop();                              // 実データ行のみに
const N = lines.length;

const cuts = JSON.parse(fs.readFileSync(cutsPath, 'utf8'));

// ── 被覆検証: 昇順・隙間なし・重複なし・全行 ──
let expect = 1;
for (const c of cuts) {
  if (c.start !== expect) { console.error(`FATAL: gap/overlap at line ${expect} (got start=${c.start} for ${c.out})`); process.exit(1); }
  if (c.end < c.start) { console.error(`FATAL: end<start in ${JSON.stringify(c)}`); process.exit(1); }
  expect = c.end + 1;
}
if (expect !== N + 1) { console.error(`FATAL: coverage ends at ${expect - 1}, file has ${N} lines`); process.exit(1); }

// ── 書き出し ──
const slice = (s, e) => lines.slice(s - 1, e).join('\n') + '\n';
let template = '';
const written = [];
for (const c of cuts) {
  const body = slice(c.start, c.end);
  if (c.out === 'template') { template += body; continue; }
  const p = path.join(outDir, c.out);
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, body, 'latin1');
  written.push(c.out);
  template += `{{include:${c.out}}}\n`;
}
fs.mkdirSync(path.join(outDir, 'src'), { recursive: true });
fs.writeFileSync(path.join(outDir, 'src', 'template.html'), template, 'latin1');
console.log(`OK: template + ${written.length} fragments -> ${outDir}`);
```

- [ ] **Step 3: フィクスチャで実行して検証**

```bash
cd /f/Htlml/3DGS/Locahun3D && node tools/split/extract.mjs tools/split/fixtures/mini.html tools/split/fixtures/mini-cuts.json /tmp/mini-out
cat /tmp/mini-out/src/template.html
```
Expected: `OK: template + 2 fragments`。template.htmlは1-2行目原文＋`{{include:src/css/010_main.css}}`＋4-5行目原文＋`{{include:src/js/010_a.js}}`＋8行目原文。

- [ ] **Step 4: 被覆エラーが落ちることを確認**

mini-cuts.jsonの2番目のstartを一時的に4へ書き換えて実行:
```bash
node tools/split/extract.mjs tools/split/fixtures/mini.html /tmp/bad-cuts.json /tmp/mini-out2
```
Expected: `FATAL: gap/overlap at line 3` で exit 1。確認後、正しいcutsに戻す。

- [ ] **Step 5: Commit**

```bash
git add tools/split && git commit -m "feat(split): extraction tool with full-coverage validation"
```

---

### Task 3: 連結ビルド build.mjs（フィクスチャでバイト一致検証）

**Files:**
- Create: `build.mjs`（リポジトリルート）

- [ ] **Step 1: build.mjs を実装**

```js
// 単一HTML組み立てビルド。src/template.html の {{include:path}} 行を
// 各断片ファイルの中身で置換して Locahun3D_OfflineViewer.html を出力する。
// バイト保存のため一貫して latin1 で読み書きする（EOL変換なし）。
// 使い方: node build.mjs [--force] [--src <dir>] [--out <file>]
//   --force: 出力先が前回ビルド後に手編集されていても上書きする
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const args = process.argv.slice(2);
const opt = (name, dflt) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : dflt; };
const FORCE   = args.includes('--force');
const ROOT    = path.dirname(fileURLToPath(import.meta.url));
const SRC     = opt('--src', path.join(ROOT, 'src'));
const BASE    = path.dirname(SRC);   // include相対パス(src/js/...)の基準 = srcの親
const OUT     = opt('--out', path.join(ROOT, 'Locahun3D_OfflineViewer.html'));
const HASHREC = path.join(ROOT, '.build-hash');

const sha = (buf) => crypto.createHash('sha256').update(buf).digest('hex');

// ── 手編集ガード: 出力先が前回ビルド結果と違うなら停止 ──
if (!FORCE && fs.existsSync(OUT) && fs.existsSync(HASHREC)) {
  const rec = fs.readFileSync(HASHREC, 'utf8').trim();
  const cur = sha(fs.readFileSync(OUT));
  if (rec && cur !== rec) {
    console.error('FATAL: output file was modified since last build (hotfix?).');
    console.error('       Port the change into src/ first, or rerun with --force to discard it.');
    process.exit(1);
  }
}

const template = fs.readFileSync(path.join(SRC, 'template.html'), 'latin1');
let missing = 0;
const html = template.replace(/^\{\{include:(.+?)\}\}\n/gm, (_m, rel) => {
  const p = path.join(BASE, rel);
  if (!fs.existsSync(p)) { console.error(`FATAL: missing fragment ${rel}`); missing++; return ''; }
  const body = fs.readFileSync(p, 'latin1');
  if (body.length === 0) { console.error(`FATAL: empty fragment ${rel}`); missing++; return ''; }
  return body;
});
if (missing) process.exit(1);
if (html.includes('{{include:')) { console.error('FATAL: unresolved {{include:}} marker remains'); process.exit(1); }

fs.writeFileSync(OUT, html, 'latin1');
fs.writeFileSync(HASHREC, sha(fs.readFileSync(OUT)) + '\n');
console.log(`OK: built ${OUT} (${(html.length / 1024).toFixed(0)} KB)`);
```

- [ ] **Step 2: フィクスチャでラウンドトリップ一致を確認**

```bash
cd /f/Htlml/3DGS/Locahun3D && node build.mjs --src /tmp/mini-out/src --out /tmp/mini-rebuilt.html
sha256sum tools/split/fixtures/mini.html /tmp/mini-rebuilt.html
```
Expected: **SHA完全一致**。

- [ ] **Step 3: ガードが働くことを確認**

```bash
node tools/split/extract.mjs tools/split/fixtures/mini.html tools/split/fixtures/mini-cuts.json /tmp/mini-out
rm /tmp/mini-out/src/js/010_a.js && node build.mjs --src /tmp/mini-out/src --out /tmp/mini-rebuilt2.html
```
Expected: `FATAL: missing fragment` exit 1。
次に手編集ガード（HASHRECはリポジトリルート共有なので、この順で連続実行する）:
```bash
node tools/split/extract.mjs tools/split/fixtures/mini.html tools/split/fixtures/mini-cuts.json /tmp/mini-out   # 断片を復元
node build.mjs --src /tmp/mini-out/src --out /tmp/mini-rebuilt.html      # .build-hash が rebuilt を指す
printf x >> /tmp/mini-rebuilt.html                                       # 手編集を模擬
node build.mjs --src /tmp/mini-out/src --out /tmp/mini-rebuilt.html
```
Expected: 最後のビルドが `FATAL: output file was modified since last build` exit 1。`--force` 付きなら成功することも確認。

- [ ] **Step 4: Commit**

```bash
git add build.mjs .gitignore && git commit -m "feat: single-file concat build with tamper guard"
```
（`.build-hash` は .gitignore に追加する）

---

### Task 4: 切断リスト自動生成 tools/split/gen-cuts.mjs

**Files:**
- Create: `tools/split/gen-cuts.mjs`

- [ ] **Step 1: 実装**

```js
// 正本HTMLから cuts.json の下書きを生成する。
// ルール:
//  - <style>...</style> の中身 → src/css/NNN_style_block.css（タグ行はtemplate残し）
//  - importmap / MIXAMO_GLB_B64 のscript中身 → assets/ へ
//  - <script type="module"> の中身 → // ══ セクションマーカー境界で src/js/NNN_<slug>.js
//  - その他すべて template
// 使い方: node tools/split/gen-cuts.mjs <original.html> > tools/split/cuts.json
import fs from 'node:fs';

const orig = fs.readFileSync(process.argv[2], 'latin1');
const lines = orig.split('\n'); lines.pop();
const N = lines.length;
const L = (i) => lines[i - 1]; // 1-based

// ── 特徴行を走査 ──
const styleRanges = [];   // {open, close} タグ行番号
const events = [];
let styleOpen = 0;
let moduleOpen = 0, moduleClose = 0, importmapOpen = 0, importmapClose = 0, mixamoLine = 0;
for (let i = 1; i <= N; i++) {
  const t = L(i);
  if (/^<style>/.test(t)) styleOpen = i;
  if (/^<\/style>/.test(t) && styleOpen) { styleRanges.push({ open: styleOpen, close: i }); styleOpen = 0; }
  if (/MIXAMO_GLB_B64/.test(t)) mixamoLine = i;
  if (/<script type="importmap">/.test(t)) importmapOpen = i;
  if (importmapOpen && !importmapClose && i > importmapOpen && /^<\/script>/.test(t)) importmapClose = i;
  if (/<script type="module">/.test(t)) moduleOpen = i;
}
for (let i = N; i >= 1; i--) if (/^<\/script>/.test(L(i))) { moduleClose = i; break; }

// ── moduleスクリプト内のセクション境界 ──
// セクション頭は「marker / タイトル / marker」の3行構造。1本目のmarker行 =
// 自分がmarker・前行が非marker・2行後がmarker、で判定する。
const isM = (i) => i >= 1 && i <= N && /^\/\/ ═/.test(L(i));
const secStarts = [];
for (let i = moduleOpen + 1; i < moduleClose; i++) {
  if (isM(i) && !isM(i - 1) && isM(i + 2)) secStarts.push(i);
}
const slug = (title) => (title.replace(/^\/\/\s*/, '').replace(/[^A-Za-z0-9]+/g, '_')
  .replace(/^_+|_+$/g, '').toLowerCase() || 'section').slice(0, 40);

// ── cuts組み立て ──
const cuts = [];
let cursor = 1;
const pushTemplate = (upto) => { if (upto >= cursor) { cuts.push({ out: 'template', start: cursor, end: upto }); cursor = upto + 1; } };
const pushOut = (out, start, end) => { pushTemplate(start - 1); cuts.push({ out, start, end }); cursor = end + 1; };

let cssIdx = 0;
const marks = [];
for (const r of styleRanges) if (r.close > r.open + 1) marks.push({ s: r.open + 1, e: r.close - 1, out: `src/css/${String(++cssIdx * 10).padStart(3, '0')}_style_block.css` });
if (importmapClose > importmapOpen + 1) marks.push({ s: importmapOpen + 1, e: importmapClose - 1, out: 'src/assets/importmap.json' });
if (mixamoLine) marks.push({ s: mixamoLine, e: mixamoLine, out: 'src/assets/mixamo_glb_b64.html' });
let jsIdx = 0;
for (let k = 0; k < secStarts.length; k++) {
  const s = k === 0 ? moduleOpen + 1 : secStarts[k];
  const e = k + 1 < secStarts.length ? secStarts[k + 1] - 1 : moduleClose - 1;
  const title = slug(L(secStarts[k] + 1) || `sec${k}`);
  marks.push({ s, e, out: `src/js/${String(++jsIdx * 10).padStart(3, '0')}_${title}.js` });
}
marks.sort((a, b) => a.s - b.s);
for (const m of marks) pushOut(m.out, m.s, m.e);
pushTemplate(N);

process.stdout.write(JSON.stringify(cuts, null, 1) + '\n');
console.error(`sections=${jsIdx} css=${cssIdx} total_cuts=${cuts.length}`);
```

- [ ] **Step 2: 実行して下書き生成・妥当性を目視**

```bash
cd /f/Htlml/3DGS/Locahun3D && node tools/split/gen-cuts.mjs Locahun3D_OfflineViewer.html > tools/split/cuts.json
node -e "const c=require('./tools/split/cuts.json');console.log(c.filter(x=>x.out!=='template').map(x=>x.out+' ('+(x.end-x.start+1)+'L)').join('\n'))"
```
Expected: 約45個のjsファイル＋css＋assets。**stderrのsections数が40〜50の範囲**であること。0や数個ならマーカー検出の正規表現がずれている（`grep -n '^// ═' Locahun3D_OfflineViewer.html | head` で実際の文字を確認して修正）。

- [ ] **Step 3: Commit**

```bash
git add tools/split/gen-cuts.mjs tools/split/cuts.json && git commit -m "feat(split): cuts.json draft generator"
```

---

### Task 5: cuts.json精緻化 → 本番抽出 → SHA一致ゲート

**Files:**
- Modify: `tools/split/cuts.json`
- Create: `src/`（抽出結果一式）

- [ ] **Step 1: 800行超の断片を洗い出す**

```bash
node -e "const c=require('./tools/split/cuts.json');c.filter(x=>x.out!=='template'&&x.end-x.start+1>800).forEach(x=>console.log(x.out, x.end-x.start+1))"
```

- [ ] **Step 2: 超過セクションをサブ分割**

各超過セクションについて `// ──` サブセクション境界を探し、cuts.jsonのそのエントリを2〜3個に手分割する（`out` は `310_camera_tool.js` → `310_camera_tool.js` / `311_camera_tool_capture.js` のように末尾+1連番）。START/ENDには**Step 1で表示された該当エントリのstart/end**を入れる:
```bash
awk -v s=START -v e=END 'NR>=s && NR<=e && /^\/\/ ──|^  \/\/ ──/ {print NR": "$0}' Locahun3D_OfflineViewer.html
```
分割点はトップレベルの `// ──` コメント行の直前。**関数の途中で切らないこと**（前後数行を読んで確認）。誤っても次StepのSHAゲートで検出される（連結順は同じなのでSHAは一致する — ここでの誤りは「ファイル境界が不自然」という可読性の問題のみ。ただしstart/endの打ち間違いはextractの被覆検証が捕まえる）。

- [ ] **Step 3: HTML本体も分割（任意だが推奨）**

template残りの巨大範囲（HTML本体 ~2,300行）を確認し、パネル/モーダル単位のトップレベルコメント境界で `src/html/NNN_*.html` エントリを数個追加する:
```bash
node -e "const c=require('./tools/split/cuts.json');c.filter(x=>x.out==='template'&&x.end-x.start+1>400).forEach(x=>console.log(x.start+'-'+x.end, x.end-x.start+1+'L'))"
```
タグの途中で切らない。境界は `<!-- ... -->` トップレベルコメント行の直前。

- [ ] **Step 4: 本番抽出**

```bash
node tools/split/extract.mjs Locahun3D_OfflineViewer.html tools/split/cuts.json .
```
Expected: `OK: template + <n> fragments`。被覆エラーが出たらstart/endを修正して再実行。

- [ ] **Step 5: SHA一致ゲート（合格条件）**

```bash
cp Locahun3D_OfflineViewer.html /tmp/original-backup.html
node build.mjs --force
sha256sum /tmp/original-backup.html Locahun3D_OfflineViewer.html
```
Expected: **SHA-256完全一致**。不一致なら `diff <(xxd /tmp/original-backup.html) <(xxd Locahun3D_OfflineViewer.html) | head` で最初の差分バイトを特定し、cuts.jsonを修正 → Step 4からやり直し。一致するまで先に進まない。

- [ ] **Step 6: 全断片が800行以下であることを確認**

```bash
find src -name '*.js' -o -name '*.css' -o -name '*.html' | xargs wc -l | sort -rn | head -5
```
Expected: 最大でも800前後（テンプレート除く）。超過があればStep 2へ戻る（SHAゲート再実行を忘れない）。

- [ ] **Step 7: Commit**

```bash
git add src tools/split/cuts.json .build-hash 2>/dev/null; git add src tools/split/cuts.json
git commit -m "refactor: split viewer into src/ fragments (byte-identical build verified)"
```

---

### Task 6: GENERATEDバナー

**Files:**
- Modify: `src/template.html:1`

- [ ] **Step 1: template.htmlの1行目（doctype行）の直後にバナー行を挿入**

```html
<!-- GENERATED FILE — DO NOT EDIT. Source: src/ in F:\Htlml\3DGS\Locahun3D (build: node build.mjs) -->
```

- [ ] **Step 2: ビルドして差分がバナー1行だけであることを確認**

```bash
node build.mjs && diff /tmp/original-backup.html Locahun3D_OfflineViewer.html
```
Expected: 追加1行のみの差分。

- [ ] **Step 3: Commit**

```bash
git add src/template.html Locahun3D_OfflineViewer.html && git commit -m "chore: add GENERATED banner to built artifact"
```

---

### Task 7: デプロイ組み込みと実機スモーク

**Files:**
- Modify: `deploy-viewer.sh`（冒頭のSync節の前に build を追加）

- [ ] **Step 1: deploy-viewer.sh の `echo "=== Syncing viewer-dist ==="` の直前に追加**

```bash
echo "=== Building single-file viewer ==="
node "$DIR/build.mjs"
```

- [ ] **Step 2: 新リポジトリからデプロイ**

```bash
cd /f/Htlml/3DGS/Locahun3D && bash deploy-viewer.sh
```
Expected: build OK → 1 asset uploaded → Version ID表示。

- [ ] **Step 3: 実機スモーク（ブラウザ・スクショ検証必須）**

viewer.locahun3d.com をハードリロードし、以下を確認してスクショを撮る:
1. 配信HTMLの先頭にGENERATEDバナーがあること（`curl -s https://viewer.locahun3d.com/Locahun3D_OfflineViewer | head -3`）
2. 空プロジェクトを開く → カメラ / 日照 / 測定 / カメラワーク 各パネルの開閉
3. オブジェクト追加（cube）→ 移動ギズモ表示 → ZIP保存が動く
4. コンソールに新規エラーがないこと

Expected: すべて正常（バイト一致＋バナーのみなので理論上変化なし。これは配信経路の確認）。

- [ ] **Step 4: push**

```bash
git push
```

---

### Task 8: 同期先の切替とドキュメント・メモリ更新

**Files:**
- Modify: `F:\Htlml\3DGS\locahun3d_online\public\viewer\offline-viewer.html`（成果物コピー）
- Modify: Dropbox側リポジトリ（`git pull` で受け皿化）
- Modify: メモリ `project_locahun3d_viewer.md` ほか

- [ ] **Step 1: オンラインrepoへ成果物を同期・commit・push**

```bash
cp /f/Htlml/3DGS/Locahun3D/Locahun3D_OfflineViewer.html /f/Htlml/3DGS/locahun3d_online/public/viewer/offline-viewer.html
cd /f/Htlml/3DGS/locahun3d_online && git add public/viewer/offline-viewer.html && git commit -m "sync: viewer from new build pipeline" && git push
```

- [ ] **Step 2: Dropbox側を受け皿に更新**

```bash
cd "/f/UNDEFINED Dropbox/UNDEFINED/Works/MFF/01_ProjectFile/3DGS" && git status --short && git pull
```
未コミット変更が残っていてpullが失敗する場合はユーザーに確認してから stash/破棄。以後Dropbox側では編集しない（閲覧・他PC共有・Sanrioコピー元のみ）。

- [ ] **Step 3: メモリ更新**

`C:\Users\askgg\.claude\projects\F--\memory\project_locahun3d_viewer.md` に追記: 作業場所=`F:\Htlml\3DGS\Locahun3D\`、修正フロー=src/編集→`node build.mjs`→実機確認→commit+push→deploy、成果物直接編集禁止（ビルドが警告して止まる）、Dropbox側は受け皿。必要なら新メモリ `project_viewer_module_split.md` を作りMEMORY.mdへ索引追加。

- [ ] **Step 4: 完了報告**

ユーザーへ: 新しい修正フロー・SHA一致で無変更が証明されたこと・凍結解除を報告。
