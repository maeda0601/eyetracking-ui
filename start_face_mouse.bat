@echo off
rem ============================================================
rem 顔マウス 起動用バッチファイル
rem ダブルクリックで起動する。どのフォルダから実行してもよい
rem   1. 仮想環境（.venv）が無ければ uv sync で作成する
rem   2. モデルファイルが無ければ scripts\download_model.py で取得する
rem   3. 仮想環境の Python で scripts\face_mouse.py を起動する
rem      （オフライン環境でも動くよう uv run ではなく直接起動する）
rem 終了は Ctrl+Alt+Q。この黒い画面を閉じても終了する
rem ============================================================
setlocal
chcp 932 > nul
title 顔マウス（この画面を閉じると終了します）

rem このバッチファイルのあるフォルダ（プロジェクトフォルダ）へ移動
cd /d "%~dp0"

set "VENV_PYTHON=%~dp0.venv\Scripts\python.exe"

rem --- 初回: 仮想環境の作成 ---
if not exist "%VENV_PYTHON%" (
    echo 初回セットアップ: 依存パッケージを導入しています（数分かかります）...
    call :find_uv
    if errorlevel 1 goto :error
    "%UV%" sync
    if errorlevel 1 (
        echo.
        echo [エラー] 仮想環境の作成に失敗しました。
        echo ネットワークに接続できない場合は、マニュアル 第2部 3章の手順でインストールしてください。
        goto :error
    )
)

rem --- 初回: モデルファイルの取得 ---
if not exist "models\face_landmarker.task" (
    echo 初回セットアップ: 顔検出モデルを取得しています...
    "%VENV_PYTHON%" scripts\download_model.py
    if errorlevel 1 goto :error
)

echo 顔マウスを起動します。
echo 画面上部中央に「顔マウス：無効（両目2秒で有効）」と出れば起動しています。
echo 終了は Ctrl+Alt+Q です。この画面は最小化しておいてください。
echo.
"%VENV_PYTHON%" scripts\face_mouse.py
if errorlevel 1 goto :error

endlocal
exit /b 0

rem --- uv を探す（PATH に無ければ標準のインストール先を使う）---
:find_uv
set "UV=uv"
where uv > nul 2>&1
if not errorlevel 1 exit /b 0
if exist "%USERPROFILE%\.local\bin\uv.exe" (
    set "UV=%USERPROFILE%\.local\bin\uv.exe"
    exit /b 0
)
if exist "%LOCALAPPDATA%\Programs\uv\uv.exe" (
    set "UV=%LOCALAPPDATA%\Programs\uv\uv.exe"
    exit /b 0
)
echo.
echo [エラー] uv が見つかりません。次のどちらかでインストールしてください。
echo   pip install uv
echo   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 ^| iex"
echo 分からない場合は導入担当者に連絡してください（マニュアル 第2部 2章・3章）。
exit /b 1

:error
echo.
echo 上のメッセージを確認してください。何かキーを押すと閉じます。
pause > nul
endlocal
exit /b 1
