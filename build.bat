@echo off
REM VoiceInk Windows — Build standalone .exe

if not exist "venv\Scripts\activate.bat" (
    echo Virtual environment not found. Please run setup.bat first.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
pip install pyinstaller --quiet

REM ── Kill any running instance and clear locked dist folder ──
echo Stopping any running VoiceInk instance...
powershell -Command "Stop-Process -Name VoiceInk -Force -ErrorAction SilentlyContinue; Remove-Item -Recurse -Force 'dist\VoiceInk' -ErrorAction SilentlyContinue" >nul 2>&1

python build.py
pause
