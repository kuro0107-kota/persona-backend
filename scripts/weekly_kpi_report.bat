@echo off
chcp 65001 >nul
REM Persona 週次KPIレポートバッチ
set BACKEND_DIR=c:\Users\kouta\OneDrive\デスクトップ\New business\tinder-proxy-war\backend
set PYTHON=%BACKEND_DIR%\venv\Scripts\python.exe
set PYTHONUTF8=1
cd /d "%BACKEND_DIR%"
echo [%date% %time%] Running weekly KPI report...
"%PYTHON%" scripts\weekly_kpi_report.py
echo [%date% %time%] Done.
