#!/usr/bin/env bash
# ============================================================
#  PLY -> RAD 変換ツールキット 初回セットアップ (macOS / Linux)
# ============================================================
#   1. Node / Rust / Git の存在チェック
#   2. Spark リポジトリをクローン
#   3. 依存をインストール + Rust ツールチェーンをビルド
# ============================================================

set -e
cd "$(dirname "$0")"

echo
echo "============================================================"
echo "  PLY -> RAD 変換ツールキット セットアップ"
echo "============================================================"
echo

# ── 1. node ──
if ! command -v node >/dev/null 2>&1; then
  echo "[NG] Node.js が見つかりません。https://nodejs.org/ja から v18+ をインストールしてください。"
  exit 1
fi
echo "[OK] Node.js   : $(node --version)"

# ── 2. npm ──
if ! command -v npm >/dev/null 2>&1; then
  echo "[NG] npm が見つかりません。Node.js インストールに含まれているはずです。"
  exit 1
fi
echo "[OK] npm       : $(npm --version)"

# ── 3. cargo (Rust) ──
if ! command -v cargo >/dev/null 2>&1; then
  echo "[NG] Rust の cargo が見つかりません。"
  echo "     以下を実行してから再度このスクリプトを起動してください:"
  echo "       curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
  echo "       source \$HOME/.cargo/env"
  exit 1
fi
echo "[OK] Rust cargo: $(cargo --version)"

# ── 4. git ──
if ! command -v git >/dev/null 2>&1; then
  echo "[NG] Git が見つかりません。"
  echo "     macOS: xcode-select --install"
  echo "     Linux: sudo apt-get install git (or your distro's equivalent)"
  exit 1
fi
echo "[OK] Git       : $(git --version)"

echo
echo "すべての必要環境が揃っています。"
echo

# ── 5. spark/ サブフォルダのクローン or 更新 ──
if [ -d "spark/.git" ]; then
  echo "[INFO] spark/ フォルダは既に存在します。git pull で更新します..."
  (cd spark && git pull) || echo "[WARN] git pull に失敗しました。既存の spark/ をそのまま使用します。"
elif [ -d "spark" ]; then
  echo "[WARN] spark/ は存在しますが Git リポジトリではありません。"
  echo "       手動で削除してから再実行してください: rm -rf spark"
  exit 1
else
  echo "[INFO] Spark リポジトリをクローンしています..."
  echo "       (ネット速度により数十秒〜数分かかる場合があります)"
  git clone --depth 1 https://github.com/sparkjsdev/spark.git
fi
echo "[OK] Spark リポジトリ準備完了"

echo
echo "[INFO] Spark の依存をインストール + Rust ツールチェーンをビルドします..."
echo "       (初回は 5〜15 分かかります)"
echo

(cd spark && npm install)

# ── 6. input / output フォルダ ──
mkdir -p input output

echo
echo "============================================================"
echo "  セットアップ完了!"
echo "============================================================"
echo
echo "  次のステップ:"
echo "  1. PLY ファイルを input/ フォルダに入れる"
echo "  2. ./convert.sh を実行"
echo "  3. output/ に .rad ファイルが生成されます"
echo
