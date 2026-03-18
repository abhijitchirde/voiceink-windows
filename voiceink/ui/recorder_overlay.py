"""
Mini recorder overlay — floating pill with animated waveform.

Shows:
  - Left dot: red (recording) or yellow (transcribing/enhancing)
  - Animated waveform bars driven by real audio levels
  - Close button (top-right)
"""

import ctypes
import ctypes.wintypes
import math
import random
import time
import tkinter as tk
from typing import Optional, Callable

from voiceink.services.engine import RecordingState


# --- Colours ---
BG_PILL     = "#1e1e2e"   # dark grey/charcoal pill background
BORDER_CLR  = "#2e2e42"   # subtle dark border
ICON_CLR    = "#ffffff"   # white icon
WAVE_REC    = "#ffffff"   # white waveform bars when recording
WAVE_TRANS  = "#f59e0b"   # amber/yellow waveform bars when transcribing
WAVE_DIM    = "#3a3a55"   # dim colour for idle bars
CLOSE_CLR   = "#64647a"
CLOSE_HOV   = "#a0a0b8"

# --- Waveform layout ---
NUM_BARS    = 18
BAR_WIDTH   = 2
BAR_GAP     = 3            # 3px gap prevents rounded caps from touching
BAR_MAX_H   = 30          # max bar height — nearly full pill height
BAR_MIN_H   = 2
WAVE_W      = NUM_BARS * (BAR_WIDTH + BAR_GAP) - BAR_GAP
WAVE_H      = BAR_MAX_H + 4

# Status dot
DOT_SIZE    = 10   # diameter of the status dot in pixels
DOT_REC     = "#ef4444"  # red when recording
DOT_TRANS   = "#f59e0b"  # yellow when transcribing (matches WAVE_TRANS)

# Close button size (drawn as a compact ×)
CLOSE_SIZE  = 10   # drawn × diameter in pixels

# Canvas sizes
ICON_SIZE   = 20   # close canvas width
ICON_GAP    = 8    # equal horizontal gap between every element AND the pill edges

# Dot canvas is just wide enough to hold the dot with equal padding
DOT_CANVAS_W = DOT_SIZE + ICON_GAP * 2  # total canvas width for dot

# Pill dimensions
PILL_W  = ICON_GAP * 3 + DOT_CANVAS_W + WAVE_W + ICON_SIZE
PILL_H  = 40



class RecorderOverlay:
    """
    Floating overlay pill.
    Must be created on the main thread.
    All public update methods are safe to call from any thread.
    """

    def __init__(self, root: tk.Tk, settings):
        self._settings = settings
        self._root = root
        self._window: Optional[tk.Toplevel] = None
        self._visible = False

        self._state = RecordingState.IDLE
        self._level_avg: float = 0.0
        self._level_peak: float = 0.0

        # Waveform bar heights (smoothed)
        self._bar_heights = [BAR_MIN_H] * NUM_BARS
        # Phase offsets for idle/transcribing animation
        self._phase_offsets = [random.uniform(0, 2 * math.pi) for _ in range(NUM_BARS)]

        self._anim_after_id: Optional[str] = None
        self._last_level_time: float = 0.0

        self.on_cancel: Optional[Callable] = None

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
        self._last_level_time = time.monotonic()

    def update_status(self, text: str):
        pass  # removed

    def set_transcription(self, raw: str, enhanced: Optional[str]):
        pass  # removed

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
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        w.configure(bg=BG_PILL)
        w.attributes("-alpha", 0.97)

        # Outer frame fills the window background
        outer = tk.Frame(w, bg=BG_PILL)
        outer.pack(fill="both", expand=True)

        # Row is centered inside the outer frame using place()
        # This ensures equal ICON_GAP on all sides with NO element stretching.
        row = tk.Frame(outer, bg=BG_PILL)
        row.place(relx=0.5, rely=0.5, anchor="center")

        # --- Left status dot canvas ---
        self._dot_canvas = tk.Canvas(
            row, width=DOT_CANVAS_W, height=PILL_H,
            bg=BG_PILL, highlightthickness=0, bd=0,
        )
        self._dot_canvas.pack(side="left", padx=(0, ICON_GAP))
        # Draw initial dot (will be updated by _refresh_ui)
        self._dot_id = self._dot_canvas.create_oval(
            DOT_CANVAS_W // 2 - DOT_SIZE // 2,
            PILL_H // 2 - DOT_SIZE // 2,
            DOT_CANVAS_W // 2 + DOT_SIZE // 2,
            PILL_H // 2 + DOT_SIZE // 2,
            fill=DOT_REC, outline="",
        )

        # --- Waveform canvas (fixed size, NOT expanded) ---
        self._wave_canvas = tk.Canvas(
            row, width=WAVE_W, height=PILL_H,
            bg=BG_PILL, highlightthickness=0, bd=0,
        )
        self._wave_canvas.pack(side="left", padx=(0, ICON_GAP))

        # --- Close canvas ---
        self._close_canvas = tk.Canvas(
            row, width=ICON_SIZE, height=PILL_H,
            bg=BG_PILL, highlightthickness=0, bd=0,
            cursor="hand2",
        )
        self._close_canvas.pack(side="left")

        self._draw_close_icon()
        self._close_canvas.bind("<Button-1>", lambda _e: self._handle_cancel())
        self._close_canvas.bind("<Enter>",
            lambda _e: self._draw_close_icon(hover=True))
        self._close_canvas.bind("<Leave>",
            lambda _e: self._draw_close_icon(hover=False))

        # Pre-create plain rectangle bars
        self._bar_ids: list[int] = []
        mid = PILL_H // 2
        for i in range(NUM_BARS):
            x0 = i * (BAR_WIDTH + BAR_GAP)
            x1 = x0 + BAR_WIDTH
            bid = self._wave_canvas.create_rectangle(
                x0, mid - BAR_MIN_H // 2,
                x1, mid + BAR_MIN_H // 2,
                fill=WAVE_REC, outline="",
            )
            self._bar_ids.append(bid)

        self._position_window()
        w.deiconify()
        w.update_idletasks()
        # Apply full pill-shaped rounded corners
        self._apply_rounded_corners(w)
        self._visible = True
        self._refresh_ui()
        self._start_animation()

    def _apply_rounded_corners(self, window: tk.Toplevel):
        """Apply a fully pill-shaped clip region (radius = PILL_H // 2) via SetWindowRgn."""
        try:
            hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
            if hwnd == 0:
                hwnd = window.winfo_id()
            radius = PILL_H // 2  # full half-circle on each end → true pill shape
            rgn = ctypes.windll.gdi32.CreateRoundRectRgn(
                0, 0, PILL_W + 1, PILL_H + 1, radius * 2, radius * 2
            )
            ctypes.windll.user32.SetWindowRgn(hwnd, rgn, True)
        except Exception:
            pass  # graceful fallback

    def _hide_main(self):
        self._stop_animation()
        if self._window:
            self._window.withdraw()
            self._visible = False

    def _position_window(self):
        if not self._window:
            return
        pos = self._settings.get_str("recorder_position") or "bottom_right"
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        margin = 24

        if pos == "bottom_right":
            x, y = sw - PILL_W - margin, sh - PILL_H - margin - 48
        elif pos == "bottom_left":
            x, y = margin, sh - PILL_H - margin - 48
        elif pos == "bottom_center":
            x, y = (sw - PILL_W) // 2, sh - PILL_H - margin - 48
        elif pos == "top_right":
            x, y = sw - PILL_W - margin, margin
        elif pos == "top_left":
            x, y = margin, margin
        else:  # center
            x, y = (sw - PILL_W) // 2, (sh - PILL_H) // 2

        self._window.geometry(f"{PILL_W}x{PILL_H}+{x}+{y}")

    # ------------------------------------------------------------------
    # Animation loop
    # ------------------------------------------------------------------

    def _start_animation(self):
        self._stop_animation()
        self._animate()

    def _stop_animation(self):
        if self._anim_after_id and self._root:
            try:
                self._root.after_cancel(self._anim_after_id)
            except Exception:
                pass
        self._anim_after_id = None

    def _animate(self):
        """Called every ~40 ms (~25 fps) to update the waveform."""
        if not self._visible or not self._window:
            return

        state = self._state
        t = time.monotonic()
        mid = PILL_H // 2

        if state == RecordingState.RECORDING:
            # Volume-reactive: amplify mic RMS → bar heights with smooth rise/fall.
            raw = self._level_avg
            age = t - self._last_level_time
            if age > 0.15:
                raw *= max(0.0, 1.0 - (age - 0.15) * 6)
            amplified = min(1.0, math.sqrt(raw * 8.0))
            colour = WAVE_REC
            for i, bid in enumerate(self._bar_ids):
                if amplified < 0.02:
                    target_h = BAR_MIN_H
                else:
                    centre_weight = 1.0 - abs(i - (NUM_BARS - 1) / 2) / ((NUM_BARS - 1) / 2) * 0.35
                    noise = random.uniform(0.80, 1.20)
                    target_h = max(BAR_MIN_H, int(BAR_MAX_H * amplified * centre_weight * noise))
                cur = self._bar_heights[i]
                alpha = 0.5 if target_h > cur else 0.25
                self._bar_heights[i] = int(cur + (target_h - cur) * alpha)
                h = self._bar_heights[i]
                x0 = i * (BAR_WIDTH + BAR_GAP)
                x1 = x0 + BAR_WIDTH
                self._wave_canvas.coords(bid, x0, mid - h // 2, x1, mid + h // 2)
                self._wave_canvas.itemconfigure(bid, fill=colour)

        elif state in (RecordingState.TRANSCRIBING, RecordingState.ENHANCING):
            # Gentle sine-wave shimmer in yellow
            colour = WAVE_TRANS
            for i, bid in enumerate(self._bar_ids):
                phase = self._phase_offsets[i]
                h = int(BAR_MIN_H + (BAR_MAX_H * 0.45) * (0.5 + 0.5 * math.sin(t * 3.5 + phase)))
                self._bar_heights[i] = h
                x0 = i * (BAR_WIDTH + BAR_GAP)
                x1 = x0 + BAR_WIDTH
                self._wave_canvas.coords(bid, x0, mid - h // 2, x1, mid + h // 2)
                self._wave_canvas.itemconfigure(bid, fill=colour)

        else:
            colour = WAVE_DIM
            for i, bid in enumerate(self._bar_ids):
                phase = self._phase_offsets[i]
                h = int(BAR_MIN_H + 2 * (0.5 + 0.5 * math.sin(t * 1.2 + phase)))
                x0 = i * (BAR_WIDTH + BAR_GAP)
                x1 = x0 + BAR_WIDTH
                self._wave_canvas.coords(bid, x0, mid - h // 2, x1, mid + h // 2)
                self._wave_canvas.itemconfigure(bid, fill=colour)

        self._anim_after_id = self._root.after(40, self._animate)

    # ------------------------------------------------------------------
    # UI refresh
    # ------------------------------------------------------------------

    def _refresh_ui(self):
        if not self._window or not self._visible:
            return
        self._draw_dot()

    def _draw_dot(self):
        """Update the status dot colour based on current state."""
        if self._state in (RecordingState.TRANSCRIBING, RecordingState.ENHANCING):
            colour = DOT_TRANS
        else:
            colour = DOT_REC
        self._dot_canvas.itemconfigure(self._dot_id, fill=colour)

    def _draw_close_icon(self, hover: bool = False):
        """Draw a compact 10×10 × on the close canvas."""
        c = self._close_canvas
        c.delete("all")
        cx, cy = ICON_SIZE // 2, PILL_H // 2
        r = CLOSE_SIZE // 2   # half-size arm reach
        col = CLOSE_HOV if hover else ICON_CLR
        lw = 1
        c.create_line(cx - r, cy - r, cx + r, cy + r,
                      fill=col, width=lw, capstyle="round")
        c.create_line(cx + r, cy - r, cx - r, cy + r,
                      fill=col, width=lw, capstyle="round")

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _handle_cancel(self):
        if self.on_cancel:
            self.on_cancel()
