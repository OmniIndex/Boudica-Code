@echo off
setlocal enabledelayedexpansion

set BOUDICA_API_KEY=
set BOUDICA_USER_ID=

cd /d "%~dp0"

echo Boudica Code - Windows Launcher
echo.

REM Remove old venv completely (handles both Linux and Windows venvs)
if exist "venv" (
    echo Removing old virtual environment...
    rmdir /s /q venv 2>nul
    timeout /t 2 /nobreak >nul
    if exist "venv" (
        echo Retrying removal...
        rmdir /s /q venv 2>nul
    )
)

REM Create fresh Windows venv
echo Creating new virtual environment...
python -m venv venv
if errorlevel 1 (
    echo Error: Failed to create virtual environment
    echo Make sure Python is installed in your PATH
    pause
    exit /b 1
)

REM Install dependencies
echo Installing dependencies...
venv\Scripts\pip install -q -r requirements.txt

REM Run the CLI
echo Starting BoudicaCode...
echo.
venv\Scripts\python src\main.py

endlocal
pause




