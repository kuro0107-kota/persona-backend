@echo off
chcp 65001 >nul
REM ============================================================
REM Persona バックエンドサーバー自動起動バッチ
REM Windowsタスクスケジューラから呼び出す
REM ============================================================

set BACKEND_DIR=c:\Users\kouta\OneDrive\デスクトップ\New business\tinder-proxy-war\backend
set PYTHON=%BACKEND_DIR%\venv\Scripts\python.exe
set PYTHONUTF8=1

cd /d "%BACKEND_DIR%"

echo [%date% %time%] Starting Persona backend server...
"%PYTHON%" -m uvicorn main:app --host 0.0.0.0 --port 8000
