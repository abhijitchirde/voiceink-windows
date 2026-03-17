"""
Mini recorder overlay — Windows equivalent of the floating MiniRecorder view.

A small, always-on-top frameless window that shows:
  - Current state (idle / recording / transcribing / enhancing)
  - Audio level bar (when recording)
  - Last transcription result
  - Cancel button
"""

import tkinter as tk
from tkinter import ttk
import threading
from typing import Optional, Callable

from voiceink.services.engine import RecordingState


# Colours (dark theme, matches VoiceInk Mac aesthetic)
BG_DARK     = "#1a1a1a"
BG_CARD     = "#2a2a2a"
ACCENT      = "#6366f1"   # indigo
ACCENT_DIM  = "#4f46e5"
SUCCESS     = "#22c55e"
ERROR_RED   = "#ef4444"
TEXT_WHITE  = "#f8fafc"
TEXT_MUTED  = "#94a3b8"
BAR_BG      = "#3f3f46"


class RecorderOverlay:
    """
    Floating overlay window.
    Must be created on the main thread.
    All update methods are safe to call from any thread.
    """

    def __init__(self, root: tk.Tk, settings):
        self._settings = settings
        self._root = root
        self._window: Optional[tk.Toplevel] = None
        self._visible = False

        self._state = RecordingState.IDLE
        self._level_avg: float = 0.0
        self._level_peak: float = 0.0
        self._status_text = ""
        self._last_transcription = ""

        self.on_cancel: Optional[Callable] = None
        self.on_copy: Optional[Callable[[str], None]] = None

        self._bar_anim_id: Optional[str] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show(self):
        self._root.after(0, self._show_main)

    def hide(self):
        self._root.after(0, self._hide_main)

    def update_state(self, state: RecordingState):
        self._state = state
        self._root.after(0, self._refresh_ui)

    def update_level(self, avg: float, peak: float):
        self._level_avg = avg
        self._level_peak = peak
        self._root.after(0, self._update_level_bar)

    def update_status(self, text: str):
        self._status_text = text
        self._root.after(0, self._refresh_ui)

    def set_transcription(self, raw: str, enhanced: Optional[str]):
        self._last_transcription = enhanced if enhanced else raw
        self._root.after(0, self._refresh_ui)

    # ------------------------------------------------------------------
    # Private — window creation
    # ------------------------------------------------------------------

    def _show_main(self):
        if self._visible and self._window:
            self._window.deiconify()
            self._window.lift()
            return

        self._window = tk.Toplevel(self._root)
        w = self._window

        w.withdraw()
        w.overrideredirect(True)      # no title bar
        w.attributes("-topmost", True)
        w.configure(bg=BG_DARK)
        w.attributes("-alpha", 0.96)

        # Rounded-corner effect via a thin border frame
        outer = tk.Frame(w, bg=ACCENT, padx=1, pady=1)
        outer.pack(fill="both", expand=True)

        inner = tk.Frame(outer, bg=BG_DARK, padx=16, pady=12)
        inner.pack(fill="both", expand=True)

        # --- Header row ---
        header = tk.Frame(inner, bg=BG_DARK)
        header.pack(fill="x")

        self._dot = tk.Label(header, text="●", bg=BG_DARK, fg=ACCENT,
                             font=("Segoe UI", 10))
        self._dot.pack(side="left")

        self._title_label = tk.Label(
            header, text="VoiceInk", bg=BG_DARK, fg=TEXT_WHITE,
            font=("Segoe UI", 11, "bold"), padx=6,
        )
        self._title_label.pack(side="left")

        cancel_btn = tk.Button(
            header, text="✕", bg=BG_DARK, fg=TEXT_MUTED,
            relief="flat", bd=0, cursor="hand2",
            font=("Segoe UI", 10),
            command=self._handle_cancel,
            activebackground=BG_DARK, activeforeground=ERROR_RED,
        )
        cancel_btn.pack(side="right")

        # --- Status label ---
        self._status_label = tk.Label(
            inner, text="Ready", bg=BG_DARK, fg=TEXT_MUTED,
            font=("Segoe UI", 9), anchor="w",
        )
        self._status_label.pack(fill="x", pady=(4, 0))

        # --- Audio level bar ---
        self._bar_frame = tk.Frame(inner, bg=BG_DARK)
        self._bar_frame.pack(fill="x", pady=(6, 0))

        self._bar_bg = tk.Canvas(
            self._bar_frame, bg=BAR_BG, height=6,
            highlightthickness=0, bd=0,
        )
        self._bar_bg.pack(fill="x")
        self._bar_fill = self._bar_bg.create_rectangle(
            0, 0, 0, 6, fill=ACCENT, outline="",
        )

        # --- Transcription text ---
        text_frame = tk.Frame(inner, bg=BG_CARD, padx=8, pady=6)
        text_frame.pack(fill="x", pady=(8, 0))

        self._text_label = tk.Label(
            text_frame,
            text="Press hotkey to start recording",
            bg=BG_CARD, fg=TEXT_WHITE,
            font=("Segoe UI", 9),
            wraplength=280,
            justify="left",
            anchor="w",
        )
        self._text_label.pack(fill="x")

        # --- Copy button ---
        self._copy_btn = tk.Button(
            inner, text="Copy", bg=BG_CARD, fg=TEXT_MUTED,
            relief="flat", bd=0, cursor="hand2",
            font=("Segoe UI", 8),
            command=self._handle_copy,
            activebackground=BG_CARD, activeforeground=TEXT_WHITE,
            pady=4,
        )
        self._copy_btn.pack(fill="x", pady=(4, 0))

        self._position_window()
        w.deiconify()
        self._visible = True
        self._refresh_ui()

    def _hide_main(self):
        if self._window:
            self._window.withdraw()
            self._visible = False

    def _position_window(self):
        if not self._window:
            return
        width, height = 320, 160
        pos = self._settings.get_str("recorder_position") or "bottom_right"
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        margin = 24

        if pos == "bottom_right":
            x, y = sw - width - margin, sh - height - margin - 48
        elif pos == "bottom_left":
            x, y = margin, sh - height - margin - 48
        elif pos == "bottom_center":
            x, y = (sw - width) // 2, sh - height - margin - 48
        elif pos == "top_right":
            x, y = sw - width - margin, margin
        elif pos == "top_left":
            x, y = margin, margin
        else:  # center
            x, y = (sw - width) // 2, (sh - height) // 2

        self._window.geometry(f"{width}x{height}+{x}+{y}")

    # ------------------------------------------------------------------
    # Private — UI refresh
    # ------------------------------------------------------------------

    def _refresh_ui(self):
        if not self._window or not self._visible:
            return

        state = self._state

        if state == RecordingState.RECORDING:
            self._dot.configure(fg=ERROR_RED)
            self._title_label.configure(text="Recording...")
            status = self._status_text or "Listening — press hotkey to stop"
            self._status_label.configure(text=status, fg=ERROR_RED)
            self._bar_frame.pack(fill="x", pady=(6, 0))
        elif state == RecordingState.TRANSCRIBING:
            self._dot.configure(fg=TEXT_MUTED)
            self._title_label.configure(text="Transcribing...")
            self._status_label.configure(
                text=self._status_text or "Processing audio...", fg=TEXT_MUTED
            )
            self._bar_frame.pack_forget()
        elif state == RecordingState.ENHANCING:
            self._dot.configure(fg=ACCENT)
            self._title_label.configure(text="Enhancing...")
            self._status_label.configure(
                text=self._status_text or "AI is enhancing...", fg=ACCENT
            )
            self._bar_frame.pack_forget()
        else:  # IDLE / ERROR
            self._dot.configure(fg=SUCCESS if self._last_transcription else ACCENT)
            self._title_label.configure(text="VoiceInk")
            self._status_label.configure(
                text=self._status_text or "Ready — press hotkey to record",
                fg=TEXT_MUTED,
            )
            self._bar_frame.pack_forget()

        if self._last_transcription:
            display = self._last_transcription[:200]
            if len(self._last_transcription) > 200:
                display += "..."
            self._text_label.configure(text=display, fg=TEXT_WHITE)
            self._copy_btn.configure(state="normal")
        else:
            self._text_label.configure(
                text="Press hotkey to start recording", fg=TEXT_MUTED
            )
            self._copy_btn.configure(state="disabled")

    def _update_level_bar(self):
        if not self._window or not self._visible:
            return
        if self._state != RecordingState.RECORDING:
            return
        try:
            bar_width = self._bar_bg.winfo_width()
            fill_width = max(4, int(bar_width * self._level_avg))
            self._bar_bg.coords(self._bar_fill, 0, 0, fill_width, 6)
            # Colour shifts red when loud
            intensity = self._level_peak
            if intensity > 0.85:
                colour = ERROR_RED
            elif intensity > 0.5:
                colour = "#f59e0b"  # amber
            else:
                colour = ACCENT
            self._bar_bg.itemconfigure(self._bar_fill, fill=colour)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _handle_cancel(self):
        if self.on_cancel:
            self.on_cancel()

    def _handle_copy(self):
        if self._last_transcription and self.on_copy:
            self.on_copy(self._last_transcription)
