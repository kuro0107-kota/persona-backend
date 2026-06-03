@echo off
chcp 65001 >nul
REM ============================================================
REM Persona 日次タスク統合ランナー
REM Windowsタスクスケジューラから毎日6:00に呼び出す
REM - SNS自動投稿
REM - コスト監視（APIコスト集計）
REM ============================================================

set BACKEND_DIR=c:\Users\kouta\OneDrive\デスクトップ\New business\tinder-proxy-war\backend
set PYTHON=%BACKEND_DIR%\venv\Scripts\python.exe
set PYTHONUTF8=1

cd /d "%BACKEND_DIR%"

echo ========================================
echo [%date% %time%] Persona Daily Runner
echo ========================================

echo [1/2] SNS Auto Post...
"%PYTHON%" scripts\daily_auto_post.py
echo.

echo [2/2] Cost Monitor...
"%PYTHON%" scripts\cost_monitor.py
echo.

echo [%date% %time%] All daily tasks done.
