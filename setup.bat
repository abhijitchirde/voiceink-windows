@echo off
REM VoiceInk Windows — One-click setup
REM Run this once to install all dependencies, then use run.bat to launch.

echo ============================================================
echo   VoiceInk Windows - Setup
echo ============================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not on PATH.
    echo Download Python 3.11+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo Python found:
python --version
echo.

REM Create virtual environment
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
    echo Done.
    echo.
)

REM Activate venv
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip --quiet

REM Install dependencies
echo Installing dependencies (this may take a few minutes)...
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR: Some dependencies failed to install.
    echo Check the error messages above.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Setup complete!
echo ============================================================
echo.
echo To run VoiceInk:   run.bat
echo To build .exe:     build.bat
echo.
pause
