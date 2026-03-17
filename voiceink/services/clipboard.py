"""
Clipboard & paste-at-cursor — Windows equivalent of CursorPaster.swift + ClipboardManager.swift.

Uses:
  - pyperclip  for clipboard read/write
  - pyautogui  for simulating Ctrl+V keypress
"""

import time
import threading
from typing import Optional

try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False


class ClipboardPaster:
    """
    Puts text onto the clipboard and optionally simulates Ctrl+V to paste it
    into whichever window had focus before VoiceInk activated.

    Mirrors Mac behaviour:
    - Optionally saves and restores the previous clipboard contents
    - Small delay before pasting to give the target window time to re-focus
    """

    def __init__(self, settings):
        self._settings = settings

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def paste_at_cursor(self, text: str):
        """Copy text to clipboard and send Ctrl+V to the focused window."""
        if not PYPERCLIP_AVAILABLE:
            return

        restore = self._settings.get_bool("restore_clipboard")
        saved = self._save_clipboard() if restore else None

        self._set_clipboard(text)

        # Small pause so the target app has focus after our window dismisses
        delay = 0.1
        timer = threading.Timer(delay, self._do_paste)
        timer.daemon = True
        timer.start()

        if restore and saved is not None:
            restore_delay = max(
                self._settings.get_float("clipboard_restore_delay") or 0.3,
                0.3,
            )
            restore_timer = threading.Timer(
                delay + restore_delay,
                lambda: self._set_clipboard(saved),
            )
            restore_timer.daemon = True
            restore_timer.start()

    def copy_to_clipboard(self, text: str):
        """Just set the clipboard — no paste simulation."""
        self._set_clipboard(text)

    def get_clipboard(self) -> Optional[str]:
        if not PYPERCLIP_AVAILABLE:
            return None
        try:
            return pyperclip.paste()
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _save_clipboard(self) -> Optional[str]:
        try:
            return pyperclip.paste()
        except Exception:
            return None

    def _set_clipboard(self, text: str):
        try:
            pyperclip.copy(text)
        except Exception:
            pass

    def _do_paste(self):
        if not PYAUTOGUI_AVAILABLE:
            return
        try:
            pyautogui.hotkey("ctrl", "v")
        except Exception:
            pass
