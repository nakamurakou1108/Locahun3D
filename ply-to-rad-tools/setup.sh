#!/usr/bin/env bash
# ============================================================
#  PLY -> RAD 変換ツールキット 初回セットアップ (macOS / Linux)
# ============================================================
#   1. Node / Rust / Git の存在チェック (Rust は無ければ自動導入)
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

# ── 3. git ──
if ! command -v git >/dev/null 2>&1; then
  echo "[NG] Git が見つかりません。"
  echo "     macOS: xcode-select --install"
  echo "     Linux: sudo apt-get install git (or your distro's equivalent)"
  exit 1
fi
echo "[OK] Git       : $(git --version)"

# ── 4. cargo (Rust) — 無ければ自動インストール ──
if ! command -v cargo >/dev/null 2>&1; then
  # 既にインストール済みだが PATH が通っていない可能性
  if [ -x "$HOME/.cargo/bin/cargo" ]; then
    export PATH="$HOME/.cargo/bin:$PATH"
  fi
fi

if ! command -v cargo >/dev/null 2>&1; then
  echo
  echo "[INFO] Rust (cargo) が見つかりません。自動インストールを行います。"
  echo "       (rustup-init を非対話モードでデフォルト構成インストール)"
  echo

  if ! command -v curl >/dev/null 2>&1; then
    echo "[NG] curl コマンドが見つかりません。手動で https://rustup.rs/ から導入してください。"
    exit 1
  fi

  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable --profile minimal
  export PATH="$HOME/.cargo/bin:$PATH"

  if ! command -v cargo >/dev/null 2>&1; then
    echo "[NG] Rust インストール後も cargo が見つかりません。"
    echo "     新しいターミナルを開き直して再実行してください。"
    exit 1
  fi
  echo "[OK] Rust 自動インストール完了"
fi
echo "[OK] Rust cargo: $(cargo --version)"

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

chmod +x convert.sh 2>/dev/null || true

echo
echo "============================================================"
echo "  セットアップ完了!"
echo "============================================================"
echo
echo "  次のステップ:"
echo "  1. 変換したい .ply / .spz / .sog ファイルのパスを指定:"
echo "       ./convert.sh path/to/file.ply"
echo "  2. 同じフォルダに <basename>.rad が生成されます"
echo
