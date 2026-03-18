"""
VoiceInk Windows — main application.

Architecture (mirrors Mac AppDelegate + MenuBarManager):
  - tkinter hidden root window (main thread UI loop)
  - pystray system tray icon (background thread)
  - RecorderOverlay (floating Toplevel)
  - SettingsWindow / HistoryWindow (Toplevels, opened on demand)
  - VoiceInkEngine (background threads for recording/transcription)
  - HotkeyManager (background thread via `keyboard` library)
"""

import sys
import threading
import tkinter as tk
from pathlib import Path
from typing import Optional

from voiceink.models.settings import settings
from voiceink.models.prompts import prompt_store
from voiceink.services.engine import VoiceInkEngine, RecordingState
from voiceink.services.hotkey_manager import HotkeyManager
from voiceink.services.clipboard import ClipboardPaster
from voiceink.ui.recorder_overlay import RecorderOverlay
from voiceink.ui.settings_window import SettingsWindow

try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False


# ── Tray icon image ──────────────────────────────────────────────────────────

def _assets_dir() -> Path:
    """Return the assets directory, works both in-source and PyInstaller bundle."""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS) / 'assets'
    return Path(__file__).parent.parent / 'assets'


def _make_tray_icon(recording: bool = False) -> "Image.Image":
    # Always use favicon.ico regardless of recording state
    icon_path = _assets_dir() / 'favicon.ico'
    if icon_path.exists():
        return Image.open(icon_path).convert('RGBA')

    # Fallback: generated icon if asset is missing
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, size - 4, size - 4], fill="#6366f1")
    cx, cy = size // 2, size // 2
    mic_w, mic_h = 12, 18
    draw.rounded_rectangle(
        [cx - mic_w // 2, cy - mic_h // 2, cx + mic_w // 2, cy + mic_h // 2],
        radius=6, fill="white",
    )
    stand_y = cy + mic_h // 2
    draw.arc([cx - 14, stand_y - 10, cx + 14, stand_y + 10], 0, 180, fill="white", width=3)
    draw.line([cx, stand_y + 10, cx, stand_y + 16], fill="white", width=3)
    draw.line([cx - 6, stand_y + 16, cx + 6, stand_y + 16], fill="white", width=3)
    return img


class VoiceInkApp:
    def __init__(self):
        # Hidden root window — keeps tkinter event loop alive
        self._root = tk.Tk()
        self._root.withdraw()
        self._root.title("VoiceInk")

        # Core services
        self._engine = VoiceInkEngine(settings, prompt_store)
        self._hotkey = HotkeyManager(settings)
        self._paster = ClipboardPaster(settings)

        # UI components
        self._overlay = RecorderOverlay(self._root, settings)
        self._settings_win = SettingsWindow(
            self._root, settings,
            on_hotkey_change=self._on_hotkey_settings_changed,
        )

        # Tray
        self._tray: Optional[pystray.Icon] = None

        self._wire_engine()
        self._wire_hotkey()
        self._wire_overlay()

    # ------------------------------------------------------------------
    # Wiring
    # ------------------------------------------------------------------

    def _wire_engine(self):
        self._engine.on_state_change = self._on_state_change
        self._engine.on_transcription = self._on_transcription
        self._engine.on_error = self._on_error
        self._engine.on_level_update = self._on_level_update
        self._engine.on_progress = self._on_progress

    def _wire_hotkey(self):
        self._hotkey.set_callbacks(
            on_start=self._engine.start_recording,
            on_stop=self._engine.stop_recording,
        )
        self._hotkey.start()

    def _wire_overlay(self):
        self._overlay.on_cancel = self._handle_cancel

    # ------------------------------------------------------------------
    # Engine callbacks (may be called from background threads)
    # ------------------------------------------------------------------

    def _on_state_change(self, state: RecordingState):
        self._overlay.update_state(state)
        if state == RecordingState.RECORDING:
            self._overlay.show()
            self._update_tray_icon(recording=True)
        elif state in (RecordingState.TRANSCRIBING, RecordingState.ENHANCING):
            self._overlay.show()
            self._update_tray_icon(recording=False)
        elif state == RecordingState.IDLE:
            self._overlay.hide()
            self._update_tray_icon(recording=False)

    def _on_transcription(self, raw: str, enhanced: Optional[str]):
        self._overlay.set_transcription(raw, enhanced)

    def _on_error(self, message: str):
        self._overlay.update_status(f"Error: {message}")
        self._root.after(0, lambda: self._show_error_briefly(message))

    def _on_level_update(self, avg: float, peak: float):
        self._overlay.update_level(avg, peak)

    def _on_progress(self, message: str):
        self._overlay.update_status(message)

    # ------------------------------------------------------------------
    # Overlay callbacks
    # ------------------------------------------------------------------

    def _handle_cancel(self):
        self._engine.cancel()
        self._hotkey.reset_state()
        self._overlay.hide()

    def _handle_copy(self, text: str):
        self._paster.copy_to_clipboard(text)

    # ------------------------------------------------------------------
    # Tray
    # ------------------------------------------------------------------

    def _build_tray(self):
        if not TRAY_AVAILABLE:
            return

        icon_img = _make_tray_icon(recording=False)

        menu = pystray.Menu(
            pystray.MenuItem("VoiceInk", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Start / Stop Recording",
                             lambda: self._engine.toggle()),
            pystray.MenuItem("Show Overlay",
                             lambda: self._root.after(0, self._overlay.show)),
            pystray.MenuItem("Settings",
                             lambda: self._root.after(0, self._settings_win.show)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._quit),
            # Hidden default item — triggered on double-click (Windows)
            pystray.MenuItem("Toggle Recording",
                             lambda: self._engine.toggle(),
                             default=True, visible=False),
        )

        self._tray = pystray.Icon(
            "VoiceInk",
            icon_img,
            "VoiceInk",
            menu=menu,
        )

        tray_thread = threading.Thread(target=self._tray.run, daemon=True)
        tray_thread.start()

    def _update_tray_icon(self, recording: bool):
        if self._tray is None:
            return
        try:
            self._tray.icon = _make_tray_icon(recording=recording)
            self._tray.title = "VoiceInk — Recording..." if recording else "VoiceInk"
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------

    def _on_hotkey_settings_changed(self):
        self._hotkey.update_hotkey()

    def _show_error_briefly(self, message: str):
        self._overlay.show()

    def _quit(self):
        self._hotkey.stop()
        if self._tray:
            self._tray.stop()
        self._root.after(0, self._root.destroy)

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def run(self):
        self._build_tray()
        # Overlay is hidden at startup; appears only when recording/transcribing
        try:
            self._root.mainloop()
        except KeyboardInterrupt:
            self._quit()
