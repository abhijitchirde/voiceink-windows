@echo off
setlocal enabledelayedexpansion
title VoiceInk Windows - Build

echo.
echo ============================================================
echo   VoiceInk Windows - Install and Build
echo ============================================================
echo.

REM ── Check Python ────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install from https://python.org
    pause & exit /b 1
)

REM ── Create venv if missing ───────────────────────────────────
if not exist "venv\Scripts\python.exe" (
    echo [1/5] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 ( echo FAILED to create venv & pause & exit /b 1 )
) else (
    echo [1/5] Virtual environment already exists, skipping.
)

REM ── Activate ─────────────────────────────────────────────────
call venv\Scripts\activate.bat

REM ── Upgrade pip ──────────────────────────────────────────────
echo [2/5] Upgrading pip...
python -m pip install --upgrade pip --quiet

REM ── Install dependencies ─────────────────────────────────────
echo [3/5] Installing dependencies (this may take a few minutes)...
pip install sounddevice numpy faster-whisper keyboard pyperclip pyautogui httpx pystray Pillow pyinstaller --quiet
if errorlevel 1 ( echo FAILED to install dependencies & pause & exit /b 1 )

REM ── Kill any running instance and clear locked dist folder ──
echo [4/5] Stopping any running VoiceInk instance...
powershell -Command "Stop-Process -Name VoiceInk -Force -ErrorAction SilentlyContinue; Remove-Item -Recurse -Force 'dist\VoiceInk' -ErrorAction SilentlyContinue" >nul 2>&1

REM ── Build exe ────────────────────────────────────────────────
echo [4/5] Building VoiceInk.exe...
python -m PyInstaller --distpath dist --workpath build_tmp --noconfirm VoiceInk.spec

if errorlevel 1 ( echo BUILD FAILED & pause & exit /b 1 )

REM ── Done ─────────────────────────────────────────────────────
echo [5/5] Done!
echo.
echo ============================================================
echo   BUILD SUCCESSFUL
echo   Executable: %CD%\dist\VoiceInk\VoiceInk.exe
echo ============================================================
echo.

REM ── Desktop shortcut ─────────────────────────────────────────
echo Create a desktop shortcut for VoiceInk? (Y/N)
set /p shortcut_choice=
if /i "!shortcut_choice!"=="Y" (
    powershell -Command "$ws=New-Object -ComObject WScript.Shell;$lnk=$ws.CreateShortcut([System.IO.Path]::Combine($env:USERPROFILE,'Desktop','VoiceInk.lnk'));$lnk.TargetPath='%CD%\dist\VoiceInk\VoiceInk.exe';$lnk.WorkingDirectory='%CD%\dist\VoiceInk';$lnk.Description='VoiceInk - Voice Transcription';$lnk.Save()"
    echo Desktop shortcut created.
) else (
    echo Skipping desktop shortcut.
)
echo.

REM ── Run now? ──────────────────────────────────────────────────
echo Run VoiceInk now? (Y/N)
set /p choice=
if /i "!choice!"=="Y" start "" "%CD%\dist\VoiceInk\VoiceInk.exe"

endlocal
