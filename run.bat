@echo off
REM Quick start script for Boudica Code (Windows)
setlocal enabledelayedexpansion

set BOUDICA_API_KEY=bdk_d69ed3b10d687b678b69c8efc29a0537a26dcdd13afd4f46e64498d5b4ad
set BOUDICA_USER_ID=sibain@omniindex.io

REM Get the script directory
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
