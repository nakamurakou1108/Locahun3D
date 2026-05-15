@echo off
REM ============================================================
REM  PLY -> RAD ドラッグ&ドロップ変換 (Windows)
REM ============================================================
REM  使い方:
REM    1. このバッチファイルを Desktop など好きな場所に置く
REM    2. 変換したい .ply / .spz / .sog ファイルを
REM       このバッチファイルにドラッグ&ドロップ
REM    3. 入力と同じフォルダに <basename>.rad が生成される
REM
REM  複数ファイルを同時ドロップしても順次処理されます。
REM  コマンドラインからの呼び出しも可:
REM    convert.bat "C:\path\to\file.ply"
REM ============================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

REM cargo bin にパスが通っていないターミナルで実行されたケースの保険
if exist "%USERPROFILE%\.cargoin\cargo.exe" (
  set "PATH=%USERPROFILE%\.cargoin;%PATH%"
)

REM ── Spark のセットアップ確認 ──
if not exist "spark\node_modules" (
  echo.
  echo [NG] Spark のセットアップが完了していません。
  echo      まず setup.bat をダブルクリックして初回セットアップを行ってください。
  echo.
  pause
  exit /b 1
)

REM ── 引数が無ければドロップを促すメッセージ ──
if "%~1"=="" (
  echo.
  echo ============================================================
  echo   PLY -^> RAD ドラッグ^&ドロップ変換
  echo ============================================================
  echo.
  echo   このバッチファイルに、変換したい .ply / .spz / .sog
  echo   ファイルをドラッグ^&ドロップしてください。
  echo.
  echo   出力 .rad は入力と同じフォルダに保存されます。
  echo.
  pause
  exit /b 0
)

REM ── ドロップされた全ファイルを順次処理 ──
echo.
echo ============================================================
echo   PLY -^> RAD 変換開始
echo ============================================================

:loop
if "%~1"=="" goto :done
call :convert_one "%~1"
shift
goto :loop

:done
echo.
echo ============================================================
echo   全ファイルの変換が完了しました。
echo ============================================================
echo.
pause
exit /b 0

REM ============================================================
REM  Sub-routine: 1 ファイル変換
REM ============================================================
:convert_one
set "SRC=%~1"
set "SRC_ABS=%~f1"
set "SRC_DIR=%~dp1"
set "SRC_NAME=%~n1"
set "SRC_EXT=%~x1"

echo.
echo ------------------------------------------------------------
echo   入力: !SRC!
echo ------------------------------------------------------------

if not exist "!SRC_ABS!" (
  echo [NG] ファイルが見つかりません: !SRC!
  goto :eof
)

REM Spark の build-lod を実行
REM 出力先は入力と同じフォルダになる(build-lod の動作)
pushd spark
call npm run build-lod -- "!SRC_ABS!" --quality
set CONV_EXIT=!errorlevel!
popd

if !CONV_EXIT! neq 0 (
  echo [NG] 変換に失敗しました: !SRC!
  goto :eof
)

REM build-lod の出力ファイル名は実装により異なる可能性があるので
REM 複数のパターンを順に探す
set "OUT_PATH="
for %%P in (
  "!SRC_DIR!!SRC_NAME!-lod.rad"
  "!SRC_DIR!!SRC_NAME!_lod.rad"
  "!SRC_DIR!!SRC_NAME!.rad"
  "!SRC_DIR!!SRC_NAME!.lod.rad"
) do (
  if exist "%%~P" if not defined OUT_PATH set "OUT_PATH=%%~P"
)

if not defined OUT_PATH (
  echo [WARN] 変換は実行されましたが、出力 .rad の場所を特定できませんでした。
  echo        以下のフォルダで *.rad を手動で探してください:
  echo        !SRC_DIR!
  goto :eof
)

REM 念のため <basename>.rad にリネーム(統一名)
set "FINAL_PATH=!SRC_DIR!!SRC_NAME!.rad"
if /i not "!OUT_PATH!"=="!FINAL_PATH!" (
  move /Y "!OUT_PATH!" "!FINAL_PATH!" >nul
)

echo [OK] 出力: !FINAL_PATH!
goto :eof
