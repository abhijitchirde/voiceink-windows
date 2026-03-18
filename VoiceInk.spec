# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

SITE = Path('venv/Lib/site-packages')

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        # ctranslate2 — copy the entire package folder so all DLLs and sub-packages are included
        (str(SITE / 'ctranslate2'), 'ctranslate2'),
        # faster_whisper assets
        (str(SITE / 'faster_whisper'), 'faster_whisper'),
        # app assets (icons, etc.)
        ('assets', 'assets'),
    ],
    hiddenimports=[
        'voiceink', 'voiceink.app',
        'voiceink.services.recorder',
        'voiceink.services.transcription',
        'voiceink.services.ai_enhancement',
        'voiceink.services.hotkey_manager',
        'voiceink.services.clipboard',
        'voiceink.services.engine',
        'voiceink.models.settings',
        'voiceink.models.transcription',
        'voiceink.models.prompts',
        'voiceink.ui.recorder_overlay',
        'voiceink.ui.settings_window',
        'voiceink.ui.history_window',
        'sounddevice', 'numpy',
        'faster_whisper',
        'ctranslate2', 'ctranslate2.models', 'ctranslate2.specs',
        'keyboard', 'pyperclip', 'pyautogui',
        'httpx', 'pystray',
        'PIL', 'PIL.Image', 'PIL.ImageDraw',
        'sqlite3',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VoiceInk',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon='assets/icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='VoiceInk',
)
