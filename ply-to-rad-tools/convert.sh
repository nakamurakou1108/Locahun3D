#!/usr/bin/env bash
# ============================================================
#  PLY -> RAD 変換 (macOS / Linux)
# ============================================================
#  使い方:
#    ./convert.sh path/to/file1.ply [path/to/file2.ply ...]
#
#  出力 .rad は入力と同じフォルダに <basename>.rad で保存されます。
#
#  macOS で Finder からダブルクリック実行したい場合は、
#  ファイルを「ターミナル.app」にドラッグするか、
#  右クリック → サービス → 「ターミナルで開く」経由で実行してください。
# ============================================================

set -e
cd "$(dirname "$0")"

# ── Spark セットアップ確認 ──
if [ ! -d "spark/node_modules" ]; then
  echo
  echo "[NG] Spark のセットアップが完了していません。"
  echo "     まず ./setup.sh を実行してください。"
  echo
  exit 1
fi

# ── 引数チェック ──
if [ $# -eq 0 ]; then
  cat <<EOF

============================================================
  PLY -> RAD 変換
============================================================

  使い方:
    ./convert.sh path/to/file1.ply [path/to/file2.ply ...]

  出力 .rad は入力と同じフォルダに保存されます。

EOF
  exit 0
fi

# ── 1 ファイル変換関数 ──
convert_one() {
  local src="$1"

  if [ ! -f "$src" ]; then
    echo "[NG] ファイルが見つかりません: $src"
    return
  fi

  # 絶対パス化
  local src_abs
  if [[ "$src" = /* ]]; then
    src_abs="$src"
  else
    src_abs="$(cd "$(dirname "$src")" && pwd)/$(basename "$src")"
  fi

  local src_dir
  src_dir="$(dirname "$src_abs")"
  local base
  base="$(basename "$src_abs")"
  local name="${base%.*}"

  echo
  echo "------------------------------------------------------------"
  echo "  入力: $src_abs"
  echo "------------------------------------------------------------"

  (
    cd spark
    npm run build-lod -- "$src_abs" --quality
  )

  # 出力ファイル候補を順に探す
  local out=""
  for candidate in \
    "${src_dir}/${name}-lod.rad" \
    "${src_dir}/${name}_lod.rad" \
    "${src_dir}/${name}.lod.rad" \
    "${src_dir}/${name}.rad"; do
    if [ -f "$candidate" ]; then
      out="$candidate"
      break
    fi
  done

  if [ -z "$out" ]; then
    echo "[WARN] 変換は実行されましたが、出力 .rad の場所を特定できませんでした。"
    echo "       以下のフォルダで *.rad を手動で探してください:"
    echo "       $src_dir"
    return
  fi

  # 念のため <basename>.rad にリネーム(統一名)
  local final="${src_dir}/${name}.rad"
  if [ "$out" != "$final" ]; then
    mv -f "$out" "$final"
  fi
  echo "[OK] 出力: $final"
}

echo
echo "============================================================"
echo "  PLY -> RAD 変換開始"
echo "============================================================"

for arg in "$@"; do
  convert_one "$arg"
done

echo
echo "============================================================"
echo "  全ファイルの変換が完了しました。"
echo "============================================================"
echo
