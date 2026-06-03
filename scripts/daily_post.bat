@echo off
chcp 65001 >nul
REM ============================================================
REM Persona SNS自動投稿バッチ（毎朝6:00にタスクスケジューラで実行）
REM ============================================================

set BACKEND_DIR=c:\Users\kouta\OneDrive\デスクトップ\New business\tinder-proxy-war\backend
set PYTHON=%BACKEND_DIR%\venv\Scripts\python.exe
set PYTHONUTF8=1

cd /d "%BACKEND_DIR%"

echo [%date% %time%] Running daily SNS auto post...
"%PYTHON%" scripts\daily_auto_post.py
echo [%date% %time%] Done.
