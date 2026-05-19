@echo off
title VisionGuard AI
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo Installing packages - first time only, may take several minutes...
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

echo.
echo Starting VisionGuard AI...
echo Your browser will open automatically in a few seconds.
echo.
echo If it does not open, type this in Chrome/Edge address bar:
echo    http://127.0.0.1:5000
echo.
echo Close this window or press Ctrl+C to stop the server.
echo.

venv\Scripts\python.exe app.py
pause
