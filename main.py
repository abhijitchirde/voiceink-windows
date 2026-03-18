"""
VoiceInk for Windows — entry point.
Run with:  python main.py
Build exe: python build.py
"""

import sys
import os

# Ensure the project root is on the path when running as a script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _ensure_single_instance():
    """
    Create a named Windows mutex to prevent multiple instances.
    If another instance is already running, show a native Windows
    message box and exit immediately.
    """
    import ctypes
    import ctypes.wintypes

    MUTEX_NAME = "Global\\VoiceInkSingleInstanceMutex"

    # CreateMutexW returns a handle; if the mutex already existed
    # GetLastError() returns ERROR_ALREADY_EXISTS (183).
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    last_error = kernel32.GetLastError()

    ERROR_ALREADY_EXISTS = 183
    if last_error == ERROR_ALREADY_EXISTS:
        # Show a native Windows message box (no tkinter needed)
        ctypes.windll.user32.MessageBoxW(
            0,
            "VoiceInk is already running.\n\nCheck the system tray icon.",
            "VoiceInk",
            0x00000040 | 0x00000000,  # MB_ICONINFORMATION | MB_OK
        )
        sys.exit(0)

    # Keep the handle alive for the lifetime of the process so the
    # mutex is not released early.
    return handle


from voiceink.app import VoiceInkApp


def main():
    _mutex_handle = _ensure_single_instance()  # noqa: F841 — must stay in scope
    app = VoiceInkApp()
    app.run()


if __name__ == "__main__":
    main()
