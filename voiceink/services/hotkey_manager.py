"""
Hotkey manager — Windows equivalent of HotkeyManager.swift.

Supports three modes (matching the Mac version exactly):
  - toggle:      press once to start, press again to stop
  - push_to_talk: hold to record, release to transcribe
  - hybrid:      short press = toggle, long press = push-to-talk

Uses the `keyboard` library for global hotkey monitoring.
The hotkey can be any key supported by the `keyboard` library
(e.g. "right ctrl", "right alt", "f9", "ctrl+shift+r").
"""

import threading
import time
from typing import Callable, Optional

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False


HYBRID_THRESHOLD = 0.5  # seconds — matches Mac's hybridPressThreshold


class HotkeyManager:
    """
    Listens for a configurable global hotkey and calls start/stop callbacks.

    Callbacks are called from a background thread — UI code must marshal
    to the main thread if needed.
    """

    def __init__(self, settings):
        self._settings = settings
        self._on_start: Optional[Callable] = None
        self._on_stop: Optional[Callable] = None

        self._current_hotkey: Optional[str] = None
        self._press_time: Optional[float] = None
        self._key_down = False
        self._is_recording = False
        self._hands_free = False
        self._lock = threading.Lock()
        self._active = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_callbacks(self, on_start: Callable, on_stop: Callable):
        self._on_start = on_start
        self._on_stop = on_stop

    def start(self):
        """Begin listening for the configured hotkey."""
        if not KEYBOARD_AVAILABLE:
            return
        self._active = True
        self._register_hotkey()

    def stop(self):
        """Stop all hotkey monitoring."""
        self._active = False
        self._unregister_hotkey()

    def update_hotkey(self):
        """Call after settings change to reload the hotkey binding."""
        if not KEYBOARD_AVAILABLE:
            return
        self._unregister_hotkey()
        if self._active:
            self._register_hotkey()

    @property
    def hotkey_display(self) -> str:
        key = self._settings.get_str("hotkey_key") or "right ctrl"
        return key.replace("_", " ").title()

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _register_hotkey(self):
        key = self._settings.get_str("hotkey_key") or "right ctrl"
        self._current_hotkey = key
        try:
            keyboard.on_press_key(key, self._on_key_down, suppress=False)
            keyboard.on_release_key(key, self._on_key_up, suppress=False)
        except Exception:
            pass  # key name not recognised — silently ignore

    def _unregister_hotkey(self):
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        self._current_hotkey = None

    def _on_key_down(self, event):
        # Verify the event key name matches exactly (handles left vs right keys).
        if self._current_hotkey and hasattr(event, "name"):
            if event.name != self._current_hotkey:
                return
        with self._lock:
            if self._key_down:
                return  # already pressed (key repeat)
            self._key_down = True
            press_time = time.monotonic()
            self._press_time = press_time
            mode = self._settings.get_str("hotkey_mode") or "hybrid"

            if mode == "toggle":
                if not self._is_recording:
                    self._is_recording = True
                    self._hands_free = True
                    self._fire(self._on_start)
                else:
                    # Second press — stop recording
                    self._hands_free = False
                    self._is_recording = False
                    self._fire(self._on_stop)

            elif mode == "push_to_talk":
                if not self._is_recording:
                    self._is_recording = True
                    self._fire(self._on_start)

            elif mode == "hybrid":
                if self._hands_free and self._is_recording:
                    # Second press in hands-free toggle mode — stop
                    self._hands_free = False
                    self._is_recording = False
                    self._fire(self._on_stop)
                elif not self._is_recording:
                    self._is_recording = True
                    self._fire(self._on_start)

    def _on_key_up(self, event):
        if self._current_hotkey and hasattr(event, "name"):
            if event.name != self._current_hotkey:
                return
        with self._lock:
            if not self._key_down:
                return
            self._key_down = False
            mode = self._settings.get_str("hotkey_mode") or "hybrid"
            press_duration = (
                time.monotonic() - self._press_time
                if self._press_time is not None
                else 0.0
            )
            self._press_time = None

            if mode == "toggle":
                pass  # start/stop both handled on key-down

            elif mode == "push_to_talk":
                if self._is_recording:
                    self._is_recording = False
                    self._fire(self._on_stop)

            elif mode == "hybrid":
                if self._is_recording:
                    if press_duration >= HYBRID_THRESHOLD:
                        # Long press = push-to-talk: stop now
                        self._hands_free = False
                        self._is_recording = False
                        self._fire(self._on_stop)
                    else:
                        # Short press = toggle: keep recording (hands-free)
                        self._hands_free = True

    def _fire(self, callback: Optional[Callable]):
        if callback:
            t = threading.Thread(target=callback, daemon=True)
            t.start()

    def reset_state(self):
        """Called when recording is forcibly stopped externally."""
        with self._lock:
            self._is_recording = False
            self._hands_free = False
            self._key_down = False
            self._press_time = None
