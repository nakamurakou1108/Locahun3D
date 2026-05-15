#!/usr/bin/env bash
# ============================================================
#  PLY -> RAD 一括変換 (macOS / Linux)
# ============================================================
#  使い方:
#    ./convert.sh                  ... input/ 内の全ファイルを変換
#    ./convert.sh path/to/file.ply ... 指定したファイルだけ変換
# ============================================================

set -e
cd "$(dirname "$0")"

# ── Spark セットアップ確認 ──
if [ ! -d "spark/node_modules" ]; then
  echo "[NG] Spark のセットアップが完了していないようです。"
  echo "     まず ./setup.sh を実行してください。"
  exit 1
fi

mkdir -p input output

# ── 1 ファイル変換関数 ──
convert_one() {
  local src="$1"
  local base
  base="$(basename "$src")"
  local name="${base%.*}"

  echo
  echo "------------------------------------------------------------"
  echo "  変換中: $src"
  echo "------------------------------------------------------------"

  # build-lod に絶対パスで渡す。spark/ ディレクトリ内で実行するので
  # 相対パスを ../ で再構成する。
  local src_abs
  if [[ "$src" = /* ]]; then
    src_abs="$src"
  else
    src_abs="$(pwd)/$src"
  fi

  (
    cd spark
    npm run build-lod -- "$src_abs" --quality
  )

  # 出力先候補を探す: build-lod は通常入力と同じディレクトリに
  # <basename>-lod.rad / <basename>.rad / <basename>_lod.rad で出す
  local out
  for candidate in \
    "$(dirname "$src_abs")/${name}-lod.rad" \
    "$(dirname "$src_abs")/${name}_lod.rad" \
    "$(dirname "$src_abs")/${name}.rad"; do
    if [ -f "$candidate" ]; then
      out="$candidate"
      break
    fi
  done

  if [ -z "${out:-}" ]; then
    echo "[WARN] 変換は走りましたが、出力 .rad の場所を特定できませんでした。"
    echo "       入力と同じフォルダで *.rad を探してください。"
    return
  fi

  mv "$out" "output/${name}.rad"
  echo "[OK] 出力: output/${name}.rad"
}

# ── 引数があれば単一ファイル変換 ──
if [ $# -gt 0 ]; then
  convert_one "$1"
  echo
  echo "完了しました。"
  exit 0
fi

# ── input/ 内の対応形式を全て処理 ──
found=0
shopt -s nullglob
for ext in ply spz sog; do
  for f in input/*.$ext; do
    convert_one "$f"
    found=1
  done
done

if [ "$found" -eq 0 ]; then
  echo
  echo "[INFO] input/ フォルダに .ply / .spz / .sog ファイルがありません。"
  echo "       変換したいファイルを input/ に入れてから再実行してください。"
fi

echo
echo "完了しました。"
