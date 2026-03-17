@echo off
REM VoiceInk Windows — Build standalone .exe

if not exist "venv\Scripts\activate.bat" (
    echo Virtual environment not found. Please run setup.bat first.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
pip install pyinstaller --quiet
python build.py
pause
