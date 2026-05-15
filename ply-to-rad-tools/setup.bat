@echo off
REM ============================================================
REM  PLY -> RAD 変換ツールキット 初回セットアップ (Windows)
REM ============================================================
REM   1. Node / Rust / Git の存在チェック (Rust は無ければ自動導入)
REM   2. Spark リポジトリをクローン
REM   3. 依存をインストール + Rust ツールチェーンをビルド
REM
REM   このスクリプトは初回 1 回だけ実行すれば OK です。
REM   完了後は convert.bat だけで変換できます。
REM ============================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ============================================================
echo   PLY -^> RAD 変換ツールキット セットアップ
echo ============================================================
echo.

REM ── 1. node の確認 ──
where node >nul 2>&1
if errorlevel 1 (
  echo [NG] Node.js が見つかりません。
  echo      https://nodejs.org/ja から v18+ をインストールしてください。
  goto :error
)
for /f "delims=" %%v in ('node --version') do set NODE_VER=%%v
echo [OK] Node.js   : !NODE_VER!

REM ── 2. npm の確認 ──
where npm >nul 2>&1
if errorlevel 1 (
  echo [NG] npm が見つかりません。Node.js インストールに含まれているはずです。
  goto :error
)
for /f "delims=" %%v in ('npm --version') do set NPM_VER=%%v
echo [OK] npm       : !NPM_VER!

REM ── 3. git の確認 ──
where git >nul 2>&1
if errorlevel 1 (
  echo [NG] Git が見つかりません。
  echo      https://git-scm.com/ からインストールしてください。
  goto :error
)
for /f "delims=" %%v in ('git --version') do set GIT_VER=%%v
echo [OK] Git       : !GIT_VER!

REM ── 4. cargo (Rust) の確認 / 無ければ自動インストール ──
where cargo >nul 2>&1
if errorlevel 1 (
  echo.
  echo [INFO] Rust ^(cargo^) が見つかりません。自動インストールを行います。
  echo        ^(rustup-init.exe をダウンロードしてデフォルト構成でインストール^)
  echo.

  set "RUSTUP_TMP=%TEMP%\rustup-init.exe"

  echo [INFO] rustup-init.exe をダウンロード中...
  where curl >nul 2>&1
  if errorlevel 1 (
    echo [NG] curl コマンドが見つかりません ^(Windows 10 1803+ に標準搭載^)。
    echo      手動で https://rustup.rs/ からインストールしてください。
    goto :error
  )
  curl.exe -fSL -o "!RUSTUP_TMP!" https://win.rustup.rs/x86_64
  if errorlevel 1 (
    echo [NG] rustup-init.exe のダウンロードに失敗しました。
    echo      ネットワークを確認するか、手動で https://rustup.rs/ から導入してください。
    goto :error
  )

  echo [INFO] Rust をインストール中... ^(数分かかります^)
  "!RUSTUP_TMP!" -y --default-toolchain stable --profile minimal
  set RUSTUP_EXIT=!errorlevel!
  del /f /q "!RUSTUP_TMP!" >nul 2>&1
  if !RUSTUP_EXIT! neq 0 (
    echo [NG] Rust インストールに失敗しました ^(exit !RUSTUP_EXIT!^)。
    echo      手動で https://rustup.rs/ から導入してください。
    goto :error
  )

  REM PATH に cargo bin を追加(現セッション用)
  set "PATH=%USERPROFILE%\.cargo\bin;!PATH!"

  where cargo >nul 2>&1
  if errorlevel 1 (
    echo [NG] Rust インストール直後にも cargo が見つかりません。
    echo      一度ターミナルを閉じて setup.bat を再実行してください。
    goto :error
  )
  echo [OK] Rust 自動インストール完了
)
for /f "delims=" %%v in ('cargo --version') do set CARGO_VER=%%v
echo [OK] Rust cargo: !CARGO_VER!

echo.
echo すべての必要環境が揃っています。
echo.

REM ── 5. spark/ サブフォルダの確認 / クローン ──
if exist "spark\.git" (
  echo [INFO] spark/ フォルダは既に存在します。git pull で更新します...
  pushd spark
  git pull
  if errorlevel 1 (
    echo [WARN] git pull に失敗しました。既存の spark/ をそのまま使用します。
  )
  popd
) else (
  if exist "spark\" (
    echo [WARN] spark/ フォルダは存在しますが Git リポジトリではありません。
    echo        既存の spark/ を削除してクローンし直すには、手動で削除してから再実行してください。
    goto :error
  )
  echo [INFO] Spark リポジトリをクローンしています...
  echo        ^(ネット速度により数十秒～数分かかる場合があります^)
  git clone --depth 1 https://github.com/sparkjsdev/spark.git
  if errorlevel 1 (
    echo [NG] git clone に失敗しました。
    goto :error
  )
)
echo [OK] Spark リポジトリ準備完了

echo.
echo [INFO] Spark の依存をインストール ^+ Rust ツールチェーンをビルドします...
echo        ^(初回は 5～15 分かかります^)
echo.

pushd spark
call npm install
set NPM_INSTALL_EXIT=!errorlevel!
popd

if !NPM_INSTALL_EXIT! neq 0 (
  echo.
  echo [NG] npm install に失敗しました。
  echo      上記のエラーメッセージを確認してください。
  goto :error
)

echo.
echo ============================================================
echo   セットアップ完了 ^!
echo ============================================================
echo.
echo   次のステップ:
echo   1. 変換したい .ply / .spz / .sog ファイルを
echo      convert.bat にドラッグ^&ドロップ
echo   2. 入力と同じフォルダに ^<basename^>.rad が生成されます
echo.
pause
exit /b 0

:error
echo.
echo ============================================================
echo   セットアップ失敗
echo ============================================================
echo.
pause
exit /b 1
