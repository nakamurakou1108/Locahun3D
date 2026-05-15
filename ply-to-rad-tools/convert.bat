@echo off
REM ============================================================
REM  PLY -> RAD 一括変換 (Windows)
REM ============================================================
REM  使い方:
REM    convert.bat                  ... input/ 内の全ファイルを変換
REM    convert.bat path\to\file.ply ... 指定したファイルだけ変換
REM ============================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

REM ── spark フォルダ存在チェック ──
if not exist "spark\node_modules" (
  echo [NG] Spark のセットアップが完了していないようです。
  echo      まず setup.bat を実行してください。
  pause
  exit /b 1
)

REM ── input / output フォルダ確保 ──
if not exist "input"  mkdir input
if not exist "output" mkdir output

REM ── 引数があれば単一ファイル変換 ──
if not "%~1"=="" (
  call :convert_one "%~1"
  goto :end
)

REM ── input/ 内の対応形式を全て処理 ──
set FOUND=0
for %%E in (ply spz sog) do (
  for %%F in ("input\*.%%E") do (
    if exist "%%F" (
      set FOUND=1
      call :convert_one "%%F"
    )
  )
)

if !FOUND! equ 0 (
  echo.
  echo [INFO] input\ フォルダに .ply / .spz / .sog ファイルがありません。
  echo        変換したいファイルを input\ に入れてから再実行してください。
  echo.
)

:end
echo.
echo 完了しました。
pause
exit /b 0

REM ============================================================
REM  Sub-routine: 1 ファイル変換
REM ============================================================
:convert_one
set "SRC=%~1"
set "SRC_NAME=%~n1"
set "SRC_EXT=%~x1"
set "SRC_ABS=%~f1"

echo.
echo ------------------------------------------------------------
echo   変換中: !SRC!
echo ------------------------------------------------------------

REM Spark の build-lod を実行
pushd spark
call npm run build-lod -- "..\!SRC!" --quality
set CONV_EXIT=!errorlevel!
popd

if !CONV_EXIT! neq 0 (
  echo [NG] 変換に失敗しました: !SRC!
  goto :eof
)

REM build-lod の出力は元と同じディレクトリに <basename>-lod.rad で生成される
REM ファイル名検索: <basename>*.rad
set "OUT_PATTERN=input\!SRC_NAME!*.rad"
for %%G in ("!OUT_PATTERN!") do (
  if exist "%%G" (
    move "%%G" "output\!SRC_NAME!.rad" >nul
    echo [OK] 出力: output\!SRC_NAME!.rad
    goto :eof
  )
)

REM もし input/ に出力されなかった場合(別パスを試す)
for %%G in ("!SRC_NAME!*.rad") do (
  if exist "%%G" (
    move "%%G" "output\!SRC_NAME!.rad" >nul
    echo [OK] 出力: output\!SRC_NAME!.rad
    goto :eof
  )
)

echo [WARN] 変換は走りましたが、出力 .rad の場所を特定できませんでした。
echo        手動で *.rad を探して output\ に移動してください。
goto :eof
