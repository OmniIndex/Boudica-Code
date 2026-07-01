@echo off
REM Quick start script for Boudica Code (Windows)
setlocal enabledelayedexpansion

set BOUDICA_API_KEY=
set BOUDICA_USER_ID=

REM Get the script directory. This is the directory that this bat runs in
set SCRIPT_DIR=%~dp0

REM Create virtual environment if it doesn't exist
if not exist "%SCRIPT_DIR%venv\" (
    echo Creating virtual environment...
    python -m venv "%SCRIPT_DIR%venv"
)

REM Activate virtual environment
call "%SCRIPT_DIR%venv\Scripts\activate.bat"

REM Install dependencies
echo Installing dependencies...
pip install -q -r "%SCRIPT_DIR%requirements.txt"

REM Run the CLI
echo.
python "%SCRIPT_DIR%src\main.py"

endlocal
pause
