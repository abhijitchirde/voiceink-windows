"""
Build script — creates a standalone VoiceInk.exe using PyInstaller.

Usage:
    python build.py

Output:
    dist/VoiceInk/VoiceInk.exe   (folder with all dependencies)
    dist/VoiceInk.exe            (single-file build — slower to start)

Requirements:
    pip install pyinstaller
"""

import subprocess
import sys
import os
from pathlib import Path

ROOT = Path(__file__).parent


def build():
    print("=" * 60)
    print("  VoiceInk Windows — Build")
    print("=" * 60)

    # Check PyInstaller is available
    try:
        import PyInstaller
    except ImportError:
        print("\nPyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    dist_dir = ROOT / "dist"
    build_dir = ROOT / "build"

    args = [
        sys.executable, "-m", "PyInstaller",
        "--name", "VoiceInk",
        "--windowed",                      # no console window
        "--onedir",                        # folder build (faster startup than --onefile)
        "--distpath", str(dist_dir),
        "--workpath", str(build_dir),
        "--specpath", str(build_dir),
        "--noconfirm",
        "--clean",
        "--icon", str(ROOT / "assets" / "icon.ico"),
        "--add-data", str(ROOT / "assets") + ";assets",
        # Hidden imports that PyInstaller may miss
        "--hidden-import", "voiceink",
        "--hidden-import", "voiceink.app",
        "--hidden-import", "voiceink.services.recorder",
        "--hidden-import", "voiceink.services.transcription",
        "--hidden-import", "voiceink.services.ai_enhancement",
        "--hidden-import", "voiceink.services.hotkey_manager",
        "--hidden-import", "voiceink.services.clipboard",
        "--hidden-import", "voiceink.services.engine",
        "--hidden-import", "voiceink.models.settings",
        "--hidden-import", "voiceink.models.transcription",
        "--hidden-import", "voiceink.models.prompts",
        "--hidden-import", "voiceink.ui.recorder_overlay",
        "--hidden-import", "voiceink.ui.settings_window",
        "--hidden-import", "voiceink.ui.history_window",
        "--hidden-import", "sounddevice",
        "--hidden-import", "numpy",
        "--hidden-import", "faster_whisper",
        "--hidden-import", "keyboard",
        "--hidden-import", "pyperclip",
        "--hidden-import", "pyautogui",
        "--hidden-import", "httpx",
        "--hidden-import", "pystray",
        "--hidden-import", "PIL",
        "--hidden-import", "PIL.Image",
        "--hidden-import", "PIL.ImageDraw",
        "--hidden-import", "sqlite3",
        str(ROOT / "main.py"),
    ]

    print("\nRunning PyInstaller...")
    result = subprocess.run(args)

    if result.returncode == 0:
        exe_path = dist_dir / "VoiceInk" / "VoiceInk.exe"
        print("\n" + "=" * 60)
        print("  BUILD SUCCESSFUL")
        print(f"  Executable: {exe_path}")
        print("=" * 60)
        print("\nTo run: double-click VoiceInk.exe")
        print("Or from terminal: dist\\VoiceInk\\VoiceInk.exe")
    else:
        print("\nBuild FAILED. Check the output above for errors.")
        sys.exit(1)


if __name__ == "__main__":
    build()
