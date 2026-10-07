@echo off
rem ============================================================
rem 顔マウス 設定画面を開くバッチファイル
rem ダブルクリックで設定画面を開く（顔マウスを起動していなくても使える）
rem 保存すると、動作中の顔マウスにそのまま反映される
rem ============================================================
setlocal
chcp 932 > nul
title 顔マウス 設定

rem このバッチファイルのあるフォルダ（プロジェクトフォルダ）へ移動
cd /d "%~dp0"

rem --- セットアップ済みなら pythonw で直接開く（黒い画面を残さない）---
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" "scripts\face_mouse_settings.py"
    endlocal
    exit /b 0
)

rem --- 未セットアップなら仮想環境を作成してから開く ---
echo 初回セットアップ: 依存パッケージを導入しています（数分かかります）...
set "UV=uv"
where uv > nul 2>&1
if errorlevel 1 (
    if exist "%USERPROFILE%\.local\bin\uv.exe" (
        set "UV=%USERPROFILE%\.local\bin\uv.exe"
    ) else if exist "%LOCALAPPDATA%\Programs\uv\uv.exe" (
        set "UV=%LOCALAPPDATA%\Programs\uv\uv.exe"
    ) else (
        echo.
        echo [エラー] uv が見つかりません。導入担当者に連絡してください（マニュアル 第2部 2章・3章）。
        goto :error
    )
)
"%UV%" sync
if errorlevel 1 (
    echo.
    echo [エラー] 依存パッケージの導入に失敗しました。
    goto :error
)
start "" ".venv\Scripts\pythonw.exe" "scripts\face_mouse_settings.py"
endlocal
exit /b 0

:error
echo.
echo 上のメッセージを確認してください。何かキーを押すと閉じます。
pause > nul
endlocal
exit /b 1
