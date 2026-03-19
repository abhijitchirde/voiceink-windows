"""
Settings window — sidebar navigation, light mode, flat design.
Mirrors the macOS VoiceInk layout: left nav + right content panel.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional
from pathlib import Path
import threading
import uuid

from voiceink.services.transcription import LOCAL_MODELS, MODELS_DIR
from voiceink.services.ai_enhancement import PROVIDER_CONFIG, AVAILABLE_MODELS
from voiceink.services.recorder import AudioRecorder
from voiceink.models.prompts import Prompt, prompt_store
from voiceink.models.transcription import store as transcription_store

# ── Light Mode Palette ────────────────────────────────────────────────────────
SIDEBAR_BG    = "#F2F2F7"
SIDEBAR_HOVER = "#E5E5EA"
ACTIVE_BG     = "#6366F1"
ACTIVE_FG     = "#FFFFFF"
NAV_FG        = "#3A3A3C"
NAV_ICON      = "#8E8E93"
CONTENT_BG    = "#FFFFFF"
CARD_BG       = "#F9F9F9"
CARD_BORDER   = "#E5E5EA"
HEADING       = "#1C1C1E"
TEXT          = "#3A3A3C"
TEXT_MUTED    = "#8E8E93"
INPUT_BG      = "#FFFFFF"
INPUT_BORDER  = "#C7C7CC"
BORDER        = "#E5E5EA"
ACCENT        = "#6366F1"
ACCENT_LIGHT  = "#EEF2FF"
ERROR         = "#EF4444"
SUCCESS       = "#16A34A"

FONT         = ("Segoe UI", 10)
FONT_BOLD    = ("Segoe UI", 10, "bold")
FONT_SMALL   = ("Segoe UI", 9)
FONT_HEAD    = ("Segoe UI", 15, "bold")
FONT_SECTION = ("Segoe UI", 8, "bold")
FONT_LOGO    = ("Segoe UI", 11, "bold")

NAV_ITEMS = [
    ("\u229e", "Dashboard"),
    ("\u2261", "History"),
    ("\u25ce", "AI Models"),
    ("\u26a1", "AI Enhancement"),
    ("\u266a", "Audio Input"),
    ("\u2328", "Hotkey"),
    ("\u270e", "Prompts"),
    ("\u2699", "General"),
]


class SettingsWindow:
    def __init__(self, root: tk.Tk, settings, on_hotkey_change: Optional[Callable] = None):
        self._root = root
        self._settings = settings
        self._on_hotkey_change = on_hotkey_change
        self._window: Optional[tk.Toplevel] = None
        self._active_nav: str = "Dashboard"
        self._nav_items: dict = {}
        self._panels: dict = {}

    def show(self):
        if self._window and self._window.winfo_exists():
            self._window.lift()
            return
        self._build()

    def _build(self):
        self._active_nav = None
        self._nav_items = {}
        self._panels = {}

        w = tk.Toplevel(self._root)
        self._window = w
        w.title("VoiceInk Settings")
        w.configure(bg=CONTENT_BG)
        w.resizable(True, True)
        w.attributes("-topmost", False)
        w.geometry("1100x680")
        w.minsize(900, 560)
        try:
            import os
            ico = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icon.ico")
            w.iconbitmap(os.path.normpath(ico))
        except Exception:
            pass

        self._setup_styles()

        main = tk.Frame(w, bg=CONTENT_BG)
        main.pack(fill="both", expand=True)

        # Sidebar
        sidebar = tk.Frame(main, bg=SIDEBAR_BG, width=210)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Divider
        tk.Frame(main, bg=BORDER, width=1).pack(side="left", fill="y")

        # Content
        self._content_area = tk.Frame(main, bg=CONTENT_BG)
        self._content_area.pack(side="left", fill="both", expand=True)

        self._build_sidebar(sidebar)

        self._panels["Dashboard"]      = self._build_dashboard_panel(self._content_area)
        self._panels["History"]        = self._build_history_panel(self._content_area)
        self._panels["AI Models"]      = self._build_ai_models_panel(self._content_area)
        self._panels["AI Enhancement"] = self._build_ai_panel(self._content_area)
        self._panels["Audio Input"]    = self._build_audio_panel(self._content_area)
        self._panels["Hotkey"]         = self._build_hotkey_panel(self._content_area)
        self._panels["Prompts"]        = self._build_prompts_panel(self._content_area)
        self._panels["General"]        = self._build_general_panel(self._content_area)

        self._show_panel("Dashboard")

    # ── Styles ────────────────────────────────────────────────────────────────

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Light.TCombobox",
                        fieldbackground=INPUT_BG, background=INPUT_BG,
                        foreground=TEXT, selectbackground=ACCENT,
                        selectforeground="white", arrowcolor=TEXT_MUTED,
                        bordercolor=INPUT_BORDER, lightcolor=INPUT_BORDER,
                        darkcolor=INPUT_BORDER)
        style.map("Light.TCombobox",
                  fieldbackground=[("readonly", INPUT_BG)],
                  foreground=[("readonly", TEXT)])
        style.configure("Light.Vertical.TScrollbar",
                        background=CARD_BG, troughcolor=CARD_BG,
                        arrowcolor=TEXT_MUTED, bordercolor=BORDER)
        style.configure("Light.TNotebook", background=CONTENT_BG, borderwidth=0)
        style.configure("Light.TNotebook.Tab",
                        background=CARD_BG, foreground=TEXT_MUTED,
                        padding=[12, 5], font=FONT_SMALL)
        style.map("Light.TNotebook.Tab",
                  background=[("selected", CONTENT_BG)],
                  foreground=[("selected", ACCENT)])

    # ── Sidebar ───────────────────────────────────────────────────────────────

    def _build_sidebar(self, sidebar):
        logo = tk.Frame(sidebar, bg=SIDEBAR_BG, height=68)
        logo.pack(fill="x")
        logo.pack_propagate(False)

        name_col = tk.Frame(logo, bg=SIDEBAR_BG)
        name_col.pack(side="left", padx=(16, 0))
        tk.Label(name_col, text="VoiceInk", bg=SIDEBAR_BG, fg=HEADING,
                 font=FONT_LOGO).pack(anchor="w")
        tk.Label(name_col, text="for Windows", bg=SIDEBAR_BG, fg=TEXT_MUTED,
                 font=FONT_SMALL).pack(anchor="w")

        tk.Frame(sidebar, bg=BORDER, height=1).pack(fill="x")
        tk.Frame(sidebar, bg=SIDEBAR_BG, height=6).pack()

        for icon, label in NAV_ITEMS:
            self._nav_items[label] = self._make_nav_item(sidebar, icon, label)

    def _make_nav_item(self, parent, icon, label):
        frame = tk.Frame(parent, bg=SIDEBAR_BG, cursor="hand2")
        frame.pack(fill="x", padx=8, pady=1)

        icon_lbl = tk.Label(frame, text=icon, bg=SIDEBAR_BG, fg=NAV_ICON,
                            font=("Segoe UI Symbol", 11), width=2, anchor="center")
        icon_lbl.pack(side="left", padx=(6, 2), pady=8)

        text_lbl = tk.Label(frame, text=label, bg=SIDEBAR_BG, fg=NAV_FG,
                            font=FONT, anchor="w")
        text_lbl.pack(side="left", fill="x", expand=True, pady=8)

        item = {"frame": frame, "icon": icon_lbl, "text": text_lbl}

        def on_click(_=None):
            self._show_panel(label)

        def on_enter(_=None):
            if self._active_nav != label:
                frame.configure(bg=SIDEBAR_HOVER)
                icon_lbl.configure(bg=SIDEBAR_HOVER)
                text_lbl.configure(bg=SIDEBAR_HOVER)

        def on_leave(_=None):
            if self._active_nav != label:
                frame.configure(bg=SIDEBAR_BG)
                icon_lbl.configure(bg=SIDEBAR_BG)
                text_lbl.configure(bg=SIDEBAR_BG)

        for w in (frame, icon_lbl, text_lbl):
            w.bind("<Button-1>", on_click)
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)

        return item

    def _show_panel(self, name):
        if self._active_nav and self._active_nav in self._nav_items:
            old = self._nav_items[self._active_nav]
            old["frame"].configure(bg=SIDEBAR_BG)
            old["icon"].configure(bg=SIDEBAR_BG, fg=NAV_ICON)
            old["text"].configure(bg=SIDEBAR_BG, fg=NAV_FG)

        self._active_nav = name
        if name in self._nav_items:
            item = self._nav_items[name]
            item["frame"].configure(bg=ACTIVE_BG)
            item["icon"].configure(bg=ACTIVE_BG, fg=ACTIVE_FG)
            item["text"].configure(bg=ACTIVE_BG, fg=ACTIVE_FG)

        for panel in self._panels.values():
            panel.pack_forget()

        if name in self._panels:
            self._panels[name].pack(fill="both", expand=True)
            if name == "History" and hasattr(self, "_history_reload"):
                self._history_reload()

    # ── Utility helpers ───────────────────────────────────────────────────────

    def _recolor_tree(self, widget, bg):
        """Recursively set bg on a widget and all its children."""
        try:
            widget.configure(bg=bg)
        except Exception:
            pass
        for child in widget.winfo_children():
            self._recolor_tree(child, bg)

    # ── Layout helpers ────────────────────────────────────────────────────────

    def _make_scrollable(self, parent):
        """Pack a scrollable area into parent. Returns inner frame."""
        canvas = tk.Canvas(parent, bg=CONTENT_BG, highlightthickness=0)
        sb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview,
                           style="Light.Vertical.TScrollbar")
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg=CONTENT_BG)
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        inner.bind("<Configure>", lambda _: canvas.configure(
            scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(
            win_id, width=e.width))

        def _scroll(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

        canvas.bind("<Enter>", lambda _: canvas.bind_all("<MouseWheel>", _scroll))
        canvas.bind("<Leave>", lambda _: canvas.unbind_all("<MouseWheel>"))

        return inner

    def _panel_header(self, parent, title, subtitle=None):
        hdr = tk.Frame(parent, bg=CONTENT_BG, padx=24, pady=18)
        hdr.pack(fill="x")
        tk.Label(hdr, text=title, bg=CONTENT_BG, fg=HEADING,
                 font=FONT_HEAD).pack(anchor="w")
        if subtitle:
            tk.Label(hdr, text=subtitle, bg=CONTENT_BG, fg=TEXT_MUTED,
                     font=FONT_SMALL).pack(anchor="w", pady=(2, 0))
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x")

    def _section_label(self, parent, text):
        tk.Label(parent, text=text.upper(), bg=CONTENT_BG, fg=TEXT_MUTED,
                 font=FONT_SECTION).pack(anchor="w", padx=24, pady=(16, 4))

    def _card(self, parent):
        """Returns the padded inner frame of a bordered card."""
        wrap = tk.Frame(parent, bg=CONTENT_BG, padx=24, pady=0)
        wrap.pack(fill="x")
        border = tk.Frame(wrap, bg=CARD_BG, highlightthickness=1,
                          highlightbackground=CARD_BORDER)
        border.pack(fill="x")
        content = tk.Frame(border, bg=CARD_BG, padx=16, pady=14)
        content.pack(fill="x")
        return content

    def _entry(self, parent, textvariable=None, show=None, width=30):
        wrap = tk.Frame(parent, bg=parent["bg"], highlightthickness=1,
                        highlightbackground=INPUT_BORDER,
                        highlightcolor=ACCENT)
        tk.Entry(wrap, textvariable=textvariable, show=show,
                 bg=INPUT_BG, fg=TEXT, insertbackground=TEXT,
                 relief="flat", bd=6, font=FONT, width=width).pack(fill="x")
        return wrap

    def _combobox(self, parent, var, values, width=26):
        return ttk.Combobox(parent, textvariable=var, values=values,
                            width=width, style="Light.TCombobox",
                            state="readonly")

    def _btn(self, parent, text, command, accent=False, danger=False, **kw):
        if danger:
            bg, fg, abg = ERROR, "white", "#DC2626"
        elif accent:
            bg, fg, abg = ACCENT, "white", "#4F46E5"
        else:
            bg, fg, abg = CARD_BG, TEXT, CARD_BORDER
        return tk.Button(parent, text=text, command=command,
                         bg=bg, fg=fg, relief="flat", bd=0,
                         font=FONT, cursor="hand2", padx=14, pady=7,
                         activebackground=abg, activeforeground=fg, **kw)

    def _checkbox(self, parent, text, variable, command):
        return tk.Checkbutton(
            parent, text=text, variable=variable,
            bg=parent["bg"], fg=TEXT, selectcolor=INPUT_BG,
            activebackground=parent["bg"], activeforeground=TEXT,
            font=FONT, command=command, relief="flat",
        )

    # ── Parakeet UI helpers ───────────────────────────────────────────────────

    def _dep_banner(self, parent, lines: list, btn_text: str,
                    on_install, warn_lines: list = None, pip_cmd: str = None):
        """Renders a dependency warning banner with an install button.
        pip_cmd: the full pip install command to display and offer a Copy button for.
        Returns (banner_wrap, install_btn, progress_lbl)."""
        BANNER_BG     = "#FFF8E1"
        BANNER_BORDER = "#F59E0B"
        WARN_FG       = "#92400E"
        CODE_BG       = "#FEF3C7"

        wrap = tk.Frame(parent, bg=CONTENT_BG, padx=24, pady=0)
        wrap.pack(fill="x", pady=(0, 4))

        banner = tk.Frame(wrap, bg=BANNER_BG, highlightthickness=1,
                          highlightbackground=BANNER_BORDER)
        banner.pack(fill="x")
        inner = tk.Frame(banner, bg=BANNER_BG, padx=14, pady=10)
        inner.pack(fill="x")

        for line in lines:
            tk.Label(inner, text=line, bg=BANNER_BG, fg=WARN_FG,
                     font=FONT_SMALL, anchor="w", justify="left").pack(anchor="w")

        if warn_lines:
            for wl in warn_lines:
                tk.Label(inner, text=wl, bg=BANNER_BG, fg="#DC2626",
                         font=FONT_SMALL, anchor="w", justify="left").pack(anchor="w")

        # ── pip command display with Copy button ──────────────────────────────
        if pip_cmd:
            cmd_row = tk.Frame(inner, bg=BANNER_BG)
            cmd_row.pack(fill="x", pady=(6, 0))

            cmd_box = tk.Frame(cmd_row, bg=CODE_BG, highlightthickness=1,
                               highlightbackground=BANNER_BORDER)
            cmd_box.pack(side="left", fill="x", expand=True)
            tk.Label(cmd_box, text=pip_cmd, bg=CODE_BG, fg="#92400E",
                     font=("Consolas", 9), padx=8, pady=4,
                     anchor="w", justify="left").pack(anchor="w")

            copied_lbl = tk.Label(cmd_row, text="", bg=BANNER_BG, fg=TEXT_MUTED,
                                  font=FONT_SMALL)

            def _copy_cmd(cmd=pip_cmd):
                inner.clipboard_clear()
                inner.clipboard_append(cmd)
                copied_lbl.configure(text="\u2713 Copied!")
                inner.after(2000, lambda: copied_lbl.configure(text=""))

            copy_btn = tk.Button(
                cmd_row, text="Copy", bg=BANNER_BG, fg=WARN_FG,
                relief="flat", bd=1, font=FONT_SMALL, cursor="hand2",
                padx=8, pady=4,
                highlightthickness=1, highlightbackground=BANNER_BORDER,
                command=_copy_cmd,
            )
            copy_btn.pack(side="left", padx=(6, 0))
            copied_lbl.pack(side="left", padx=(6, 0))

        btn_row = tk.Frame(inner, bg=BANNER_BG)
        btn_row.pack(anchor="w", pady=(6, 0))

        install_btn = tk.Button(
            btn_row, text=btn_text, bg=ACCENT, fg="white",
            relief="flat", bd=0, font=FONT_SMALL, cursor="hand2",
            padx=12, pady=5, activebackground="#4F46E5", activeforeground="white",
            command=on_install,
        )
        install_btn.pack(side="left")

        progress_lbl = tk.Label(btn_row, text="", bg=BANNER_BG, fg=TEXT_MUTED,
                                 font=FONT_SMALL)
        progress_lbl.pack(side="left", padx=(10, 0))

        return wrap, install_btn, progress_lbl

    def _parakeet_card(self, parent, key: str, meta: dict,
                       is_selected: bool, is_downloaded: bool,
                       deps_ok: bool, on_action, on_delete):
        """Render one Parakeet model card. Returns (card_frame, action_btn, del_btn, bg_widgets)."""
        bg     = ACCENT_LIGHT if is_selected else CARD_BG
        border = ACCENT       if is_selected else CARD_BORDER

        cf = tk.Frame(parent, bg=bg, highlightthickness=1, highlightbackground=border)
        cf.pack(fill="x", pady=4)

        inner_p = tk.Frame(cf, bg=bg, padx=14, pady=10)
        inner_p.pack(fill="x")

        left  = tk.Frame(inner_p, bg=bg)
        left.pack(side="left", fill="x", expand=True)
        right = tk.Frame(inner_p, bg=bg)
        right.pack(side="right", padx=(8, 0))

        # Title row with badges
        title_row = tk.Frame(left, bg=bg)
        title_row.pack(fill="x")

        title_lbl = tk.Label(title_row, text=meta["display"], bg=bg, fg=HEADING,
                             font=FONT_BOLD)
        title_lbl.pack(side="left")

        BADGE_BG = ACCENT_LIGHT
        BADGE_FG = ACCENT
        tk.Frame(title_row, bg=bg, width=6).pack(side="left")
        tk.Label(title_row, text=meta["backend"].replace("_", "-"),
                 bg=BADGE_BG, fg=BADGE_FG, font=FONT_SMALL,
                 padx=5, pady=1).pack(side="left")

        if meta.get("quantization"):
            tk.Frame(title_row, bg=bg, width=4).pack(side="left")
            tk.Label(title_row, text=meta["quantization"],
                     bg=BADGE_BG, fg=BADGE_FG, font=FONT_SMALL,
                     padx=5, pady=1).pack(side="left")

        if meta.get("cuda_badge"):
            CUDA_BG = "#FEF3C7"
            CUDA_FG = "#D97706"
            label = "CUDA required" if meta["cuda_badge"] == "required" else "CUDA recommended"
            tk.Frame(title_row, bg=bg, width=4).pack(side="left")
            tk.Label(title_row, text=label,
                     bg=CUDA_BG, fg=CUDA_FG, font=FONT_SMALL,
                     padx=5, pady=1).pack(side="left")

        # Metadata line
        size_str = (f"{meta['size_mb']} MB" if meta["size_mb"] < 1000
                    else f"{meta['size_mb']/1000:.1f} GB")
        meta_parts = [meta["language"], size_str, meta["backend"].replace("_", "-")]
        if meta.get("quantization"):
            meta_parts.append(meta["quantization"])
        meta_lbl = tk.Label(left, text="  ·  ".join(meta_parts),
                            bg=bg, fg=TEXT_MUTED, font=FONT_SMALL, anchor="w")
        meta_lbl.pack(anchor="w", pady=(1, 0))

        # Description
        desc_lbl = tk.Label(left, text=meta["description"], bg=bg, fg=TEXT_MUTED,
                            font=FONT_SMALL, justify="left", anchor="w", wraplength=500)
        desc_lbl.pack(anchor="w", pady=(2, 4))

        # Speed / Accuracy dots
        bars_row  = tk.Frame(left, bg=bg)
        bars_row.pack(anchor="w")
        bar_labels, bar_spacers = [], []
        for bar_label, filled in [("Speed", meta["speed"]), ("Accuracy", meta["accuracy"])]:
            lbl = tk.Label(bars_row, text=bar_label, bg=bg, fg=TEXT_MUTED,
                           font=FONT_SMALL, width=8, anchor="w")
            lbl.pack(side="left")
            bar_labels.append(lbl)
            for i in range(5):
                tk.Frame(bars_row, bg=ACCENT if i < filled else CARD_BORDER,
                         width=8, height=5).pack(side="left", padx=1)
            spacer = tk.Frame(bars_row, bg=bg, width=14)
            spacer.pack(side="left")
            bar_spacers.append(spacer)

        # Action button
        btn_wrap = tk.Frame(right, bg=bg)
        btn_wrap.pack(anchor="center")

        if not deps_ok:
            btn_text, btn_state, btn_cursor, btn_bg = "Needs deps", "disabled", "arrow", TEXT_MUTED
        elif is_selected:
            btn_text, btn_state, btn_cursor, btn_bg = "Default", "disabled", "arrow", SUCCESS
        elif is_downloaded:
            btn_text, btn_state, btn_cursor, btn_bg = "Set as Default", "normal", "hand2", ACCENT
        else:
            btn_text, btn_state, btn_cursor, btn_bg = "Download", "normal", "hand2", ACCENT

        action_btn = tk.Button(btn_wrap, text=btn_text, bg=btn_bg, fg="white",
                               relief="flat", bd=0, font=FONT_SMALL,
                               cursor=btn_cursor, padx=10, pady=5,
                               state=btn_state,
                               activebackground="#4F46E5", activeforeground="white",
                               command=on_action)
        action_btn.pack(side="left")

        del_btn = tk.Button(btn_wrap, text="\U0001f5d1", bg=ERROR, fg="white",
                            relief="flat", bd=0, font=("Segoe UI", 9),
                            cursor="hand2", padx=6, pady=5,
                            activebackground="#DC2626", activeforeground="white",
                            command=on_delete)
        if is_downloaded:
            del_btn.pack(side="left", padx=(6, 0))

        bg_widgets = [cf, inner_p, left, right, title_row, title_lbl,
                      meta_lbl, desc_lbl, bars_row, btn_wrap,
                      *bar_labels, *bar_spacers]

        return cf, action_btn, del_btn, bg_widgets

    def _build_parakeet_nemo_section(self, parent, cur_parakeet_key_var: list,
                                      parakeet_downloaded: set,
                                      parakeet_downloading: set,
                                      on_set_parakeet_default,
                                      on_clear_parakeet,
                                      refresh_all_parakeet):
        """Build the NeMo backend section. Returns (card_registry, nemo_ok)."""
        import sys
        import threading
        from voiceink.services.parakeet_transcription import (
            PARAKEET_MODELS, check_backend_available, check_cuda_available,
            check_model_downloaded, download_parakeet_model, delete_parakeet_model,
            BACKEND_PIP_CMDS,
        )
        from tkinter import messagebox

        IS_FROZEN = getattr(sys, 'frozen', False)
        nemo_keys = [k for k, m in PARAKEET_MODELS.items() if m["backend"] == "nemo"]
        nemo_ok   = [False]

        self._section_label(parent, "NVIDIA Parakeet — NeMo Backend")

        banner_ref = [None]

        def _install_nemo():
            install_btn.configure(text="Installing\u2026", state="disabled", bg=TEXT_MUTED)
            progress_lbl.configure(text="")

            def _run():
                import subprocess
                pkgs = BACKEND_PIP_CMDS["nemo"]
                flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                proc = subprocess.Popen(
                    [sys.executable, "-m", "pip", "install"] + pkgs,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                    creationflags=flags,
                )
                while True:
                    line = proc.stdout.readline()
                    if not line and proc.poll() is not None:
                        break
                    if line.strip():
                        install_btn.after(0, lambda l=line.strip():
                                          progress_lbl.configure(text=l[:60]))
                rc = proc.wait()
                if rc == 0:
                    install_btn.after(0, _on_install_done)
                else:
                    err = (proc.stderr.read() or "Unknown error")[-120:]
                    install_btn.after(0, lambda e=err: _on_install_error(e))

            threading.Thread(target=_run, daemon=True).start()

        def _on_install_done():
            nemo_ok[0] = True
            banner_ref[0][0].pack_forget()
            refresh_all_parakeet()

        def _on_install_error(err):
            install_btn.configure(text="Retry", state="normal", bg=ERROR,
                                  activebackground="#DC2626")
            progress_lbl.configure(text=err[:80], fg=ERROR)

        if IS_FROZEN:
            info_wrap = tk.Frame(parent, bg=CONTENT_BG, padx=24)
            info_wrap.pack(fill="x", pady=(0, 4))
            info = tk.Frame(info_wrap, bg="#EFF6FF", highlightthickness=1,
                            highlightbackground="#BFDBFE")
            info.pack(fill="x")
            info_inner = tk.Frame(info, bg="#EFF6FF", padx=14, pady=8)
            info_inner.pack(fill="x")
            tk.Label(info_inner,
                     text="\u2139  Parakeet NeMo models require running VoiceInk from source.\n"
                          "   pip install is not available in the packaged app.",
                     bg="#EFF6FF", fg="#1D4ED8", font=FONT_SMALL,
                     justify="left", anchor="w").pack(anchor="w")
            nemo_ok[0] = False
            install_btn = None
            progress_lbl = None
        else:
            nemo_ok[0] = check_backend_available("nemo")
            cuda_ok = check_cuda_available()
            cuda_text = ("\u2713  CUDA GPU detected \u2014 recommended for 0.6B+ models"
                         if cuda_ok else
                         "No CUDA GPU detected \u2014 only 110M model practical on CPU")
            cuda_fg = SUCCESS if cuda_ok else TEXT_MUTED

            if not nemo_ok[0]:
                lines     = ["\u26a0  NeMo backend not installed",
                             "   Requires: nemo_toolkit[asr] + torch"]
                warn_lines = ["   \u26a0  NeMo is Linux-primary \u2014 may require WSL2 on Windows"]
                nemo_pip = "pip install " + " ".join(BACKEND_PIP_CMDS["nemo"])
                wrap, install_btn, progress_lbl = self._dep_banner(
                    parent, lines, "Install NeMo + PyTorch", _install_nemo, warn_lines,
                    pip_cmd=nemo_pip,
                )
                banner_inner = wrap.winfo_children()[0].winfo_children()[0]
                tk.Label(banner_inner, text=f"   {cuda_text}",
                         bg="#FFF8E1", fg=cuda_fg, font=FONT_SMALL, anchor="w"
                         ).pack(anchor="w", before=banner_inner.winfo_children()[-2])
                banner_ref[0] = (wrap, install_btn, progress_lbl)
            else:
                install_btn = None
                progress_lbl = None

        stack = tk.Frame(parent, bg=CONTENT_BG, padx=24)
        stack.pack(fill="x", pady=(0, 8))

        card_registry = []

        def _start_download(k):
            parakeet_downloading.add(k)
            for reg_key, cf, action_btn, del_btn, _ in card_registry:
                if reg_key == k:
                    action_btn.configure(text="Downloading\u2026", state="disabled",
                                         bg=TEXT_MUTED, activebackground=TEXT_MUTED)
                    break

            def _on_done():
                parakeet_downloading.discard(k)
                parakeet_downloaded.add(k)
                refresh_all_parakeet()

            def _on_error(err):
                parakeet_downloading.discard(k)
                for reg_key, cf, action_btn, del_btn, _ in card_registry:
                    if reg_key == k:
                        action_btn.configure(text="Retry", state="normal", bg=ERROR,
                                             activebackground="#DC2626",
                                             command=lambda key=k: _start_download(key))
                        break

            download_parakeet_model(
                k,
                on_progress=lambda _: None,
                on_done=lambda: action_btn.after(0, _on_done),
                on_error=lambda e: action_btn.after(0, _on_error, e),
            )

        for key in nemo_keys:
            meta    = PARAKEET_MODELS[key]
            is_sel  = (cur_parakeet_key_var[0] == key)
            is_dl   = key in parakeet_downloaded
            deps_ok = nemo_ok[0]

            def _make_action(k=key):
                def _action():
                    if not nemo_ok[0] or k in parakeet_downloading:
                        return
                    if k in parakeet_downloaded:
                        on_set_parakeet_default(k, "nemo")
                    else:
                        _start_download(k)
                return _action

            def _make_delete(k=key):
                def _delete():
                    if not messagebox.askyesno(
                        "Delete Model",
                        f"Delete '{PARAKEET_MODELS[k]['display']}' model files?\n"
                        "You can re-download it later.",
                        parent=self._window
                    ):
                        return
                    delete_parakeet_model(k)
                    parakeet_downloaded.discard(k)
                    if cur_parakeet_key_var[0] == k:
                        cur_parakeet_key_var[0] = None
                        on_clear_parakeet()
                    refresh_all_parakeet()
                return _delete

            cf, action_btn, del_btn, bg_w = self._parakeet_card(
                stack, key, meta, is_sel, is_dl, deps_ok,
                _make_action(), _make_delete()
            )
            card_registry.append((key, cf, action_btn, del_btn, bg_w))

        return card_registry, nemo_ok

    def _build_parakeet_community_section(self, parent, cur_parakeet_key_var: list,
                                           parakeet_downloaded: set,
                                           parakeet_downloading: set,
                                           on_set_parakeet_default,
                                           on_clear_parakeet,
                                           refresh_all_parakeet):
        """Build the Community backend section (sherpa-onnx + HF Transformers).
        Returns list of (key, cf, action_btn, del_btn, bg_widgets) tuples."""
        import sys
        import threading
        from voiceink.services.parakeet_transcription import (
            PARAKEET_MODELS, check_backend_available,
            check_model_downloaded, download_parakeet_model, delete_parakeet_model,
            BACKEND_PIP_CMDS,
        )
        from tkinter import messagebox

        IS_FROZEN = getattr(sys, 'frozen', False)
        onnx_keys = [k for k, m in PARAKEET_MODELS.items() if m["backend"] == "sherpa_onnx"]
        hf_keys   = [k for k, m in PARAKEET_MODELS.items() if m["backend"] == "transformers"]

        onnx_ok = [False]
        hf_ok   = [False]

        self._section_label(parent, "NVIDIA Parakeet \u2014 Community (sherpa-onnx \u00b7 HF Transformers)")

        card_registry = []

        def _make_install_fn(backend_key, ok_ref, banner_ref_list):
            def _install():
                install_btn_ref = banner_ref_list[0][1]
                progress_lbl_ref = banner_ref_list[0][2]
                install_btn_ref.configure(text="Installing\u2026", state="disabled", bg=TEXT_MUTED)
                progress_lbl_ref.configure(text="")

                def _run():
                    import subprocess
                    pkgs = BACKEND_PIP_CMDS[backend_key]
                    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    proc = subprocess.Popen(
                        [sys.executable, "-m", "pip", "install"] + pkgs,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                        creationflags=flags,
                    )
                    while True:
                        line = proc.stdout.readline()
                        if not line and proc.poll() is not None:
                            break
                        if line.strip():
                            install_btn_ref.after(
                                0, lambda l=line.strip():
                                progress_lbl_ref.configure(text=l[:60])
                            )
                    rc = proc.wait()
                    if rc == 0:
                        def _done():
                            ok_ref[0] = True
                            banner_ref_list[0][0].pack_forget()
                            refresh_all_parakeet()
                        install_btn_ref.after(0, _done)
                    else:
                        err = (proc.stderr.read() or "Unknown error")[-120:]
                        def _err(e=err):
                            install_btn_ref.configure(text="Retry", state="normal",
                                                       bg=ERROR, activebackground="#DC2626")
                            progress_lbl_ref.configure(text=e[:80], fg=ERROR)
                        install_btn_ref.after(0, _err)

                threading.Thread(target=_run, daemon=True).start()
            return _install

        if IS_FROZEN:
            info_wrap = tk.Frame(parent, bg=CONTENT_BG, padx=24)
            info_wrap.pack(fill="x", pady=(0, 4))
            info_inner = tk.Frame(info_wrap, bg="#EFF6FF", highlightthickness=1,
                                  highlightbackground="#BFDBFE")
            info_inner.pack(fill="x")
            info_content = tk.Frame(info_inner, bg="#EFF6FF", padx=14, pady=8)
            info_content.pack(fill="x")
            tk.Label(info_content,
                     text="\u2139  Parakeet Community models require running VoiceInk from source.",
                     bg="#EFF6FF", fg="#1D4ED8", font=FONT_SMALL,
                     justify="left", anchor="w").pack(anchor="w")
        else:
            onnx_ok[0] = check_backend_available("sherpa_onnx")
            hf_ok[0]   = check_backend_available("transformers")

            # sherpa-onnx banner
            onnx_banner_ref = [None]
            if not onnx_ok[0]:
                onnx_pip = "pip install " + " ".join(BACKEND_PIP_CMDS["sherpa_onnx"])
                wrap, btn, prog = self._dep_banner(
                    parent,
                    ["\u26a0  sherpa-onnx not installed",
                     "   Requires: sherpa-onnx (no PyTorch needed, CPU-first)"],
                    "Install sherpa-onnx",
                    _make_install_fn("sherpa_onnx", onnx_ok, onnx_banner_ref),
                    pip_cmd=onnx_pip,
                )
                onnx_banner_ref[0] = (wrap, btn, prog)

            # HF Transformers banner
            hf_banner_ref = [None]
            if not hf_ok[0]:
                hf_pip = "pip install " + " ".join(BACKEND_PIP_CMDS["transformers"])
                wrap, btn, prog = self._dep_banner(
                    parent,
                    ["\u26a0  transformers not installed (or version < 4.47)",
                     "   Requires: transformers>=4.47 + torch + torchaudio"],
                    "Install HF Transformers",
                    _make_install_fn("transformers", hf_ok, hf_banner_ref),
                    pip_cmd=hf_pip,
                )
                hf_banner_ref[0] = (wrap, btn, prog)

        def _start_download(k, backend):
            parakeet_downloading.add(k)
            for reg_key, cf, action_btn, del_btn, _ in card_registry:
                if reg_key == k:
                    action_btn.configure(text="Downloading\u2026", state="disabled",
                                         bg=TEXT_MUTED, activebackground=TEXT_MUTED)
                    break

            def _on_done():
                parakeet_downloading.discard(k)
                parakeet_downloaded.add(k)
                refresh_all_parakeet()

            def _on_error(err):
                parakeet_downloading.discard(k)
                for reg_key, cf, action_btn, del_btn, _ in card_registry:
                    if reg_key == k:
                        action_btn.configure(text="Retry", state="normal", bg=ERROR,
                                             activebackground="#DC2626",
                                             command=lambda key=k, be=backend: _start_download(key, be))
                        break

            download_parakeet_model(
                k,
                on_progress=lambda _: None,
                on_done=lambda: action_btn.after(0, _on_done),
                on_error=lambda e: action_btn.after(0, _on_error, e),
            )

        # ── sherpa-onnx cards ──────────────────────────────────────────────────
        tk.Label(parent, text="sherpa-onnx (ONNX, no PyTorch required)",
                 bg=CONTENT_BG, fg=TEXT_MUTED, font=FONT_SMALL,
                 padx=24).pack(anchor="w", pady=(8, 2))

        onnx_stack = tk.Frame(parent, bg=CONTENT_BG, padx=24)
        onnx_stack.pack(fill="x", pady=(0, 4))

        for key in onnx_keys:
            meta    = PARAKEET_MODELS[key]
            is_sel  = (cur_parakeet_key_var[0] == key)
            is_dl   = key in parakeet_downloaded
            deps_ok = onnx_ok[0]

            def _make_action(k=key):
                def _action():
                    if not onnx_ok[0] or k in parakeet_downloading:
                        return
                    if k in parakeet_downloaded:
                        on_set_parakeet_default(k, "sherpa_onnx")
                    else:
                        _start_download(k, "sherpa_onnx")
                return _action

            def _make_delete(k=key):
                def _delete():
                    if not messagebox.askyesno("Delete Model",
                        f"Delete '{PARAKEET_MODELS[k]['display']}' model files?",
                        parent=self._window):
                        return
                    delete_parakeet_model(k)
                    parakeet_downloaded.discard(k)
                    if cur_parakeet_key_var[0] == k:
                        cur_parakeet_key_var[0] = None
                        on_clear_parakeet()
                    refresh_all_parakeet()
                return _delete

            cf, action_btn, del_btn, bg_w = self._parakeet_card(
                onnx_stack, key, meta, is_sel, is_dl, deps_ok,
                _make_action(), _make_delete()
            )
            card_registry.append((key, cf, action_btn, del_btn, bg_w))

        # ── HF Transformers cards ──────────────────────────────────────────────
        tk.Frame(parent, bg=CONTENT_BG, height=8).pack()
        tk.Label(parent, text="HF Transformers CTC (official NVIDIA repos)",
                 bg=CONTENT_BG, fg=TEXT_MUTED, font=FONT_SMALL,
                 padx=24).pack(anchor="w", pady=(0, 2))

        hf_stack = tk.Frame(parent, bg=CONTENT_BG, padx=24)
        hf_stack.pack(fill="x", pady=(0, 4))

        for key in hf_keys:
            meta    = PARAKEET_MODELS[key]
            is_sel  = (cur_parakeet_key_var[0] == key)
            is_dl   = key in parakeet_downloaded
            deps_ok = hf_ok[0]

            def _make_action(k=key):
                def _action():
                    if not hf_ok[0] or k in parakeet_downloading:
                        return
                    if k in parakeet_downloaded:
                        on_set_parakeet_default(k, "transformers")
                    else:
                        _start_download(k, "transformers")
                return _action

            def _make_delete(k=key):
                def _delete():
                    if not messagebox.askyesno("Delete Model",
                        f"Delete '{PARAKEET_MODELS[k]['display']}' model files?",
                        parent=self._window):
                        return
                    delete_parakeet_model(k)
                    parakeet_downloaded.discard(k)
                    if cur_parakeet_key_var[0] == k:
                        cur_parakeet_key_var[0] = None
                        on_clear_parakeet()
                    refresh_all_parakeet()
                return _delete

            cf, action_btn, del_btn, bg_w = self._parakeet_card(
                hf_stack, key, meta, is_sel, is_dl, deps_ok,
                _make_action(), _make_delete()
            )
            card_registry.append((key, cf, action_btn, del_btn, bg_w))

        return card_registry

    # ── Dashboard ─────────────────────────────────────────────────────────────

    def _build_dashboard_panel(self, parent):
        panel = tk.Frame(parent, bg=CONTENT_BG)
        self._panel_header(panel, "Dashboard", "Your VoiceInk overview")

        scroll_wrap = tk.Frame(panel, bg=CONTENT_BG)
        scroll_wrap.pack(fill="both", expand=True)
        inner = self._make_scrollable(scroll_wrap)

        # Pull stats
        records = transcription_store.get_all(limit=10000)
        total   = len(records)
        words   = sum(len((r.text or "").split()) for r in records)
        dur     = sum(r.duration or 0 for r in records)
        wpm     = round(words / dur * 60, 1) if dur > 0 else 0.0
        saved_m = round(words / 40) if words > 0 else 0
        h, m    = saved_m // 60, saved_m % 60
        time_str = f"{h} hr, {m} min" if h else f"{m} min"

        # Hero banner
        hero = tk.Frame(inner, bg=ACCENT, padx=20, pady=18)
        hero.pack(fill="x", padx=24, pady=(20, 0))
        row = tk.Frame(hero, bg=ACCENT)
        row.pack(anchor="w")
        tk.Label(row, text="You have saved ", bg=ACCENT, fg="white",
                 font=("Segoe UI", 13)).pack(side="left")
        tk.Label(row, text=time_str, bg=ACCENT, fg="white",
                 font=("Segoe UI", 13, "bold")).pack(side="left")
        tk.Label(row, text=" with VoiceInk", bg=ACCENT, fg="white",
                 font=("Segoe UI", 13)).pack(side="left")
        tk.Label(hero, text=f"Dictated {words:,} words across {total} sessions.",
                 bg=ACCENT, fg="#C7D2FE", font=FONT_SMALL).pack(anchor="w", pady=(4, 0))

        # Stats grid
        self._section_label(inner, "Your Stats")
        grid_wrap = tk.Frame(inner, bg=CONTENT_BG, padx=24)
        grid_wrap.pack(fill="x")
        grid_wrap.columnconfigure(0, weight=1)
        grid_wrap.columnconfigure(1, weight=1)

        def stat_card(r, c, icon, title, value, desc):
            px = (0, 6) if c == 0 else (6, 0)
            cell = tk.Frame(grid_wrap, bg=CARD_BG, highlightthickness=1,
                            highlightbackground=CARD_BORDER)
            cell.grid(row=r, column=c, padx=px, pady=5, sticky="nsew")
            body = tk.Frame(cell, bg=CARD_BG, padx=14, pady=14)
            body.pack(fill="both", expand=True)
            top = tk.Frame(body, bg=CARD_BG)
            top.pack(anchor="w")
            tk.Label(top, text=icon, bg=CARD_BG, fg=ACCENT,
                     font=("Segoe UI Symbol", 12)).pack(side="left", padx=(0, 5))
            tk.Label(top, text=title, bg=CARD_BG, fg=TEXT_MUTED,
                     font=FONT_SMALL).pack(side="left")
            tk.Label(body, text=str(value), bg=CARD_BG, fg=HEADING,
                     font=("Segoe UI", 22, "bold")).pack(anchor="w", pady=(6, 2))
            tk.Label(body, text=desc, bg=CARD_BG, fg=TEXT_MUTED,
                     font=FONT_SMALL).pack(anchor="w")

        stat_card(0, 0, "\u25ce", "Sessions Recorded",   f"{total:,}",       "VoiceInk sessions completed")
        stat_card(0, 1, "\u2261", "Words Dictated",       f"{words:,}",       "words generated")
        stat_card(1, 0, "\u26a1", "Words Per Minute",     f"{wpm}",           "VoiceInk vs. typing by hand")
        stat_card(1, 1, "\u2328", "Keystrokes Saved",     f"{words * 5:,}",   "fewer keystrokes")

        tk.Frame(inner, bg=CONTENT_BG, height=24).pack()
        return panel

    # ── History ───────────────────────────────────────────────────────────────

    def _build_history_panel(self, parent):
        from tkinter import messagebox as _mb

        panel = tk.Frame(parent, bg=CONTENT_BG)
        records: list = []
        filtered: list = []
        selected_idx: list = [None]

        # Top bar
        top = tk.Frame(panel, bg=CONTENT_BG, padx=20, pady=14)
        top.pack(fill="x")
        tk.Label(top, text="History", bg=CONTENT_BG, fg=HEADING,
                 font=FONT_HEAD).pack(side="left")
        right = tk.Frame(top, bg=CONTENT_BG)
        right.pack(side="right")
        clear_btn = tk.Button(right, text="Clear All", bg=ERROR, fg="white",
                              relief="flat", bd=0, font=FONT_SMALL,
                              cursor="hand2", padx=10, pady=5,
                              activebackground="#DC2626")
        clear_btn.pack(side="right", padx=(6, 0))
        search_var = tk.StringVar()
        sf = tk.Frame(right, bg=right["bg"], highlightthickness=1,
                      highlightbackground=INPUT_BORDER)
        sf.pack(side="right")
        tk.Entry(sf, textvariable=search_var, bg=INPUT_BG, fg=TEXT,
                 insertbackground=TEXT, relief="flat", bd=6,
                 font=FONT, width=22).pack()

        tk.Frame(panel, bg=BORDER, height=1).pack(fill="x")

        # Split pane
        pane = tk.PanedWindow(panel, orient="horizontal", bg=BORDER,
                              sashwidth=1, sashrelief="flat")
        pane.pack(fill="both", expand=True)

        list_outer = tk.Frame(pane, bg=CONTENT_BG, width=300)
        pane.add(list_outer, minsize=220)

        list_canvas = tk.Canvas(list_outer, bg=CONTENT_BG, highlightthickness=0, bd=0)
        list_sb = ttk.Scrollbar(list_outer, orient="vertical",
                                command=list_canvas.yview,
                                style="Light.Vertical.TScrollbar")
        list_canvas.configure(yscrollcommand=list_sb.set)
        list_sb.pack(side="right", fill="y")
        list_canvas.pack(side="left", fill="both", expand=True)

        cards_frame = tk.Frame(list_canvas, bg=CONTENT_BG)
        cards_window = list_canvas.create_window((0, 0), window=cards_frame, anchor="nw")

        def _on_cards_configure(e):
            list_canvas.configure(scrollregion=list_canvas.bbox("all"))

        def _on_canvas_resize(e):
            list_canvas.itemconfig(cards_window, width=e.width)

        cards_frame.bind("<Configure>", _on_cards_configure)
        list_canvas.bind("<Configure>", _on_canvas_resize)

        def _bind_mousewheel(widget):
            widget.bind("<MouseWheel>", lambda e: list_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
            for child in widget.winfo_children():
                _bind_mousewheel(child)

        card_widgets: list = []  # list of (outer, cf, lbl_ts, lbl_pre) per card

        detail_outer = tk.Frame(pane, bg=CONTENT_BG)
        pane.add(detail_outer, minsize=380)

        detail_top = tk.Frame(detail_outer, bg=CONTENT_BG, padx=14, pady=10)
        detail_top.pack(fill="x")
        meta_lbl = tk.Label(detail_top,
                            text="Select a recording to view details",
                            bg=CONTENT_BG, fg=TEXT_MUTED, font=FONT_SMALL,
                            justify="left", anchor="w")
        meta_lbl.pack(side="left", fill="x", expand=True)
        btn_row = tk.Frame(detail_top, bg=CONTENT_BG)
        btn_row.pack(side="right")

        tk.Frame(detail_outer, bg=BORDER, height=1).pack(fill="x")

        detail_nb = ttk.Notebook(detail_outer, style="Light.TNotebook")
        detail_nb.pack(fill="both", expand=True)

        def _text_tab(label):
            f = tk.Frame(detail_nb, bg=CARD_BG)
            detail_nb.add(f, text=label)
            t = tk.Text(f, bg=CARD_BG, fg=TEXT, insertbackground=TEXT,
                        relief="flat", bd=12, font=FONT_SMALL,
                        wrap="word", state="disabled", highlightthickness=0)
            s = ttk.Scrollbar(f, orient="vertical", command=t.yview,
                              style="Light.Vertical.TScrollbar")
            t.configure(yscrollcommand=s.set)
            s.pack(side="right", fill="y")
            t.pack(fill="both", expand=True)
            return t

        raw_text = _text_tab("Raw Transcription")
        enh_text = _text_tab("Enhanced")

        def current_record():
            i = selected_idx[0]
            return filtered[i] if i is not None and i < len(filtered) else None

        def _select_card(idx):
            for i, (outer_w, cf, lbl_ts, lbl_pre) in enumerate(card_widgets):
                bg = ACCENT_LIGHT if i == idx else CARD_BG
                border = ACCENT if i == idx else CARD_BORDER
                cf.configure(highlightbackground=border)
                self._recolor_tree(cf, bg)
            selected_idx[0] = idx
            if idx is not None and idx < len(filtered):
                show_detail(filtered[idx])

        def rebuild_list():
            for outer_w, *_ in card_widgets:
                outer_w.destroy()
            card_widgets.clear()

            for idx, r in enumerate(filtered):
                ts = r.timestamp.strftime("%d %b  ·  %H:%M")
                dur = f"{r.duration:.0f}s"
                preview = r.text[:80].replace("\n", " ")
                if len(r.text) > 80:
                    preview += "…"

                outer = tk.Frame(cards_frame, bg=CONTENT_BG, padx=10, pady=4)
                outer.pack(fill="x")

                cf = tk.Frame(outer, bg=CARD_BG,
                              highlightthickness=1, highlightbackground=CARD_BORDER,
                              cursor="hand2")
                cf.pack(fill="x")

                inner_pad = tk.Frame(cf, bg=CARD_BG, padx=12, pady=10)
                inner_pad.pack(fill="x")

                top_row = tk.Frame(inner_pad, bg=CARD_BG)
                top_row.pack(fill="x")

                lbl_ts = tk.Label(top_row, text=ts, bg=CARD_BG, fg=TEXT_MUTED, font=FONT_SMALL)
                lbl_ts.pack(side="left")
                tk.Label(top_row, text=dur, bg=CARD_BG, fg=TEXT_MUTED, font=FONT_SMALL).pack(side="right")

                lbl_pre = tk.Label(inner_pad, text=preview, bg=CARD_BG, fg=TEXT,
                                   font=FONT_SMALL, wraplength=220, justify="left", anchor="w")
                lbl_pre.pack(fill="x", pady=(4, 0))

                i = idx  # capture
                for widget in (cf, outer, inner_pad, top_row, lbl_ts, lbl_pre):
                    widget.bind("<Button-1>", lambda e, n=i: _select_card(n))

                for child in top_row.winfo_children():
                    child.bind("<Button-1>", lambda e, n=i: _select_card(n))

                card_widgets.append((outer, cf, lbl_ts, lbl_pre))

            _bind_mousewheel(cards_frame)

        def apply_filter(*_):
            q = search_var.get().lower().strip()
            filtered[:] = [
                r for r in records
                if not q or q in r.text.lower()
                or (r.enhanced_text and q in r.enhanced_text.lower())
            ]
            rebuild_list()

        def reload():
            records[:] = transcription_store.get_all(limit=500)
            selected_idx[0] = None
            apply_filter()

        self._history_reload = reload

        def show_detail(rec):
            ts = rec.timestamp.strftime("%B %d, %Y at %H:%M")
            meta = f"{ts}  ·  {rec.duration:.1f}s  ·  {rec.transcription_model or 'unknown'}"
            if rec.ai_model:
                meta += f"  ·  AI: {rec.ai_model}"
            meta_lbl.configure(text=meta)
            for tw, txt in [(raw_text, rec.text),
                            (enh_text, rec.enhanced_text or "(No AI enhancement)")]:
                tw.configure(state="normal")
                tw.delete("1.0", "end")
                tw.insert("1.0", txt)
                tw.configure(state="disabled")


        def copy_raw():
            r = current_record()
            if r:
                self._root.clipboard_clear()
                self._root.clipboard_append(r.text)

        def copy_enhanced():
            r = current_record()
            if r:
                self._root.clipboard_clear()
                self._root.clipboard_append(r.enhanced_text or r.text)

        def delete_selected():
            r = current_record()
            if r and _mb.askyesno("Delete", "Delete this transcription?",
                                  parent=self._window):
                transcription_store.delete(r.id)
                selected_idx[0] = None
                meta_lbl.configure(text="Select a recording to view details")
                for tw in (raw_text, enh_text):
                    tw.configure(state="normal")
                    tw.delete("1.0", "end")
                    tw.configure(state="disabled")
                reload()

        def clear_all():
            if _mb.askyesno("Clear All",
                            "Delete ALL transcription history? This cannot be undone.",
                            parent=self._window):
                transcription_store.delete_all()
                reload()

        search_var.trace_add("write", apply_filter)
        clear_btn.configure(command=clear_all)

        for label, cmd, is_accent, is_danger in [
            ("Copy Raw",      copy_raw,        False, False),
            ("Copy Enhanced", copy_enhanced,   True,  False),
            ("Delete",        delete_selected, False, True),
        ]:
            bg  = ACCENT if is_accent else CARD_BG
            fg  = "white" if is_accent else (ERROR if is_danger else TEXT)
            abg = "#4F46E5" if is_accent else CARD_BORDER
            tk.Button(btn_row, text=label, command=cmd, bg=bg, fg=fg,
                      relief="flat", bd=0, font=FONT_SMALL, cursor="hand2",
                      padx=8, pady=4, activebackground=abg,
                      activeforeground=fg).pack(side="left", padx=2)

        reload()
        return panel

    # ── Transcription ─────────────────────────────────────────────────────────

    def _build_ai_models_panel(self, parent):
        panel = tk.Frame(parent, bg=CONTENT_BG)

        # ── Custom header with live "current selection" badge ─────────────────
        hdr = tk.Frame(panel, bg=CONTENT_BG, padx=24, pady=18)
        hdr.pack(fill="x")
        left_hdr = tk.Frame(hdr, bg=CONTENT_BG)
        left_hdr.pack(side="left", fill="x", expand=True)
        tk.Label(left_hdr, text="AI Models", bg=CONTENT_BG, fg=HEADING,
                 font=FONT_HEAD).pack(anchor="w")
        tk.Label(left_hdr, text="Transcription & speech-to-text settings",
                 bg=CONTENT_BG, fg=TEXT_MUTED, font=FONT_SMALL).pack(anchor="w", pady=(2, 0))

        # Badge showing current active provider/model
        badge_frame = tk.Frame(hdr, bg=ACCENT_LIGHT, padx=10, pady=5)
        badge_frame.pack(side="right", anchor="center")
        badge_lbl = tk.Label(badge_frame, text="", bg=ACCENT_LIGHT, fg=ACCENT,
                             font=FONT_BOLD)
        badge_lbl.pack()

        # Initialise cur_key_var before _update_badge so the initial call is correct
        _init_prov = self._settings.get_str("transcription_provider") or "local"
        cur_key_var = [
            self._settings.get_str("local_model_name") or "base"
            if _init_prov == "local" else None
        ]

        def _update_badge():
            prov = self._settings.get_str("transcription_provider") or "local"
            if prov == "local":
                model_name = cur_key_var[0] or self._settings.get_str("local_model_name")
                if model_name:
                    badge_lbl.configure(text=f"Local  ·  {model_name}")
                else:
                    badge_lbl.configure(text="Local  ·  no model selected")
            elif prov == "parakeet":
                from voiceink.services.parakeet_transcription import PARAKEET_MODELS
                key = self._settings.get_str("parakeet_model_key")
                label = PARAKEET_MODELS[key]["display"] if key in PARAKEET_MODELS else "no model"
                badge_lbl.configure(text=f"Parakeet  ·  {label}")
            else:
                labels = {"groq": "Groq", "openai": "OpenAI",
                          "deepgram": "Deepgram", "custom": "Custom"}
                badge_lbl.configure(text=f"Provider  ·  {labels.get(prov, prov.title())}")

        _update_badge()
        tk.Frame(panel, bg=BORDER, height=1).pack(fill="x")

        # ── Sub-tab bar ───────────────────────────────────────────────────────
        TAB_NAMES = ["Local Model", "Provider"]
        active_tab: list = ["Local Model"]

        tab_bar = tk.Frame(panel, bg=CONTENT_BG, padx=24)
        tab_bar.pack(fill="x")
        tk.Frame(panel, bg=BORDER, height=1).pack(fill="x")

        tab_content = tk.Frame(panel, bg=CONTENT_BG)
        tab_content.pack(fill="both", expand=True)

        tab_frames: dict = {}

        def switch_tab(name):
            active_tab[0] = name
            for n, btn in tab_btns.items():
                if n == name:
                    btn.configure(fg=ACCENT, font=("Segoe UI", 10, "bold"))
                    tab_underlines[n].configure(bg=ACCENT)
                else:
                    btn.configure(fg=TEXT_MUTED, font=FONT)
                    tab_underlines[n].configure(bg=CONTENT_BG)
            for n, f in tab_frames.items():
                if n == name:
                    f.place(relx=0, rely=0, relwidth=1, relheight=1)
                else:
                    f.place_forget()

        tab_btns = {}
        tab_underlines = {}
        for name in TAB_NAMES:
            col = tk.Frame(tab_bar, bg=CONTENT_BG)
            col.pack(side="left")
            btn = tk.Button(col, text=name, bg=CONTENT_BG, fg=TEXT_MUTED,
                            relief="flat", bd=0, font=FONT, cursor="hand2",
                            padx=4, pady=10, activebackground=CONTENT_BG,
                            command=lambda n=name: switch_tab(n))
            btn.pack()
            ul = tk.Frame(col, bg=CONTENT_BG, height=2)
            ul.pack(fill="x")
            tab_btns[name] = btn
            tab_underlines[name] = ul
            tk.Frame(tab_bar, bg=CONTENT_BG, width=16).pack(side="left")

        # ── Local Model tab ───────────────────────────────────────────────────
        local_frame = tk.Frame(tab_content, bg=CONTENT_BG)
        tab_frames["Local Model"] = local_frame

        lm_scroll_wrap = tk.Frame(local_frame, bg=CONTENT_BG)
        lm_scroll_wrap.pack(fill="both", expand=True)
        lm_inner = self._make_scrollable(lm_scroll_wrap)

        self._section_label(lm_inner, "Whisper Models (runs locally, no internet required)")

        display_map = {v["display"]: k for k, v in LOCAL_MODELS.items()}

        MODEL_DESCS = {
            "tiny":     "Fastest, lowest accuracy. Best for quick drafts.",
            "base":     "Good balance of speed and accuracy. Recommended for most users.",
            "small":    "Better accuracy, moderate speed. Great for clear speech.",
            "medium":   "High accuracy, slower. Ideal for complex vocabulary.",
            "large-v3": "Best accuracy available. Slowest, requires more RAM.",
        }
        SPEED_BARS  = {k: int(v["speed"] / 5 * 5) for k, v in LOCAL_MODELS.items()}
        ACC_BARS    = {k: int(v["accuracy"] * 5) for k, v in LOCAL_MODELS.items()}

        model_card_frames: dict = {}
        model_action_btns: dict = {}   # key -> action Button widget
        model_delete_btns: dict = {}   # key -> delete icon Button widget
        model_bg_widgets: dict = {}    # key -> list of (widget, is_text) to recolor
        _downloading: set = set()      # keys currently being downloaded
        # Snapshot of download state — checked from disk once on open, then
        # updated only on explicit download/delete. Never re-checked mid-session
        # to avoid filesystem noise flipping card states unexpectedly.
        _downloaded: set = set()       # keys confirmed downloaded on disk

        def _hf_snapshot_dir(key):
            """Return the HuggingFace model cache root dir for a model, or None."""
            folder = f"models--Systran--faster-whisper-{key}"
            import os as _os
            candidates = []
            hf_hub_cache = _os.environ.get("HUGGINGFACE_HUB_CACHE")
            hf_home = _os.environ.get("HF_HOME")
            if hf_hub_cache:
                candidates.append(Path(hf_hub_cache) / folder)
            elif hf_home:
                candidates.append(Path(hf_home) / "hub" / folder)
            candidates.append(Path.home() / ".cache" / "huggingface" / "hub" / folder)
            for cache_dir in candidates:
                snapshots = cache_dir / "snapshots"
                if not snapshots.exists():
                    continue
                for snap in snapshots.iterdir():
                    if (snap / "model.bin").exists():
                        return cache_dir  # return the whole model cache root
            return None

        def check_downloaded(key):
            # Check manual MODELS_DIR first
            if (MODELS_DIR / key).exists() and (MODELS_DIR / key / "model.bin").exists():
                return True
            # Then check HuggingFace disk cache directly (no huggingface_hub needed)
            return _hf_snapshot_dir(key) is not None

        # Populate _downloaded once from disk at panel build time
        for _k in LOCAL_MODELS:
            if check_downloaded(_k):
                _downloaded.add(_k)

        def _refresh_all_cards():
            """Update every card's bg and button state. Does NOT touch bar dot frames."""
            current = cur_key_var[0]  # None when a cloud provider is active
            for k in model_card_frames:
                is_cur = (current is not None and k == current)
                in_progress = k in _downloading
                bg     = ACCENT_LIGHT if is_cur else CARD_BG
                border = ACCENT       if is_cur else CARD_BORDER
                model_card_frames[k].configure(highlightbackground=border)
                for widget in model_bg_widgets.get(k, []):
                    try:
                        widget.configure(bg=bg)
                    except Exception:
                        pass
                btn = model_action_btns[k]
                if in_progress:
                    # Leave the "Downloading…" button state untouched
                    if k in model_delete_btns:
                        model_delete_btns[k].pack_forget()
                    continue
                # For the default card trust cur_key_var — skip disk check
                if is_cur:
                    btn.configure(text="Default", bg=SUCCESS, fg="white",
                                  activebackground=SUCCESS, activeforeground="white",
                                  cursor="arrow", state="disabled")
                    if k in model_delete_btns:
                        model_delete_btns[k].pack(side="left", padx=(6, 0))
                    continue
                # For all other cards use the stable _downloaded set (no disk re-check)
                dl = k in _downloaded
                if dl:
                    btn.configure(text="Set as Default", bg=ACCENT, fg="white",
                                  activebackground="#4F46E5", activeforeground="white",
                                  cursor="hand2", state="normal")
                else:
                    btn.configure(text="Download", bg=ACCENT, fg="white",
                                  activebackground="#4F46E5", activeforeground="white",
                                  cursor="hand2", state="normal")
                if k in model_delete_btns:
                    if dl:
                        model_delete_btns[k].pack(side="left", padx=(6, 0))
                    else:
                        model_delete_btns[k].pack_forget()

        def set_default(key):
            cur_key_var[0] = key
            self._settings.set("local_model_name", key)
            self._settings.set("transcription_provider", "local")
            _refresh_all_cards()
            _update_badge()

        def download_and_set(key):
            if key in _downloading:
                return  # already in progress, ignore duplicate clicks
            _downloading.add(key)
            btn = model_action_btns[key]
            btn.configure(text="Downloading…", state="disabled", fg="white",
                          bg=TEXT_MUTED, activebackground=TEXT_MUTED,
                          activeforeground="white")
            def _do():
                try:
                    from faster_whisper import WhisperModel
                    WhisperModel(key, device="cpu", compute_type="int8")
                    def _done():
                        _downloading.discard(key)
                        _downloaded.add(key)
                        _refresh_all_cards()
                    btn.after(0, _done)
                except Exception:
                    def _on_err():
                        _downloading.discard(key)
                        btn.configure(text="Retry", bg=ERROR, fg="white",
                                      activebackground=ERROR, activeforeground="white",
                                      cursor="hand2", state="normal",
                                      command=lambda k=key: download_and_set(k))
                    btn.after(0, _on_err)
            threading.Thread(target=_do, daemon=True).start()

        def on_action_btn(key):
            if key in _downloading:
                return  # download in progress, ignore
            if key in _downloaded:
                set_default(key)
            else:
                download_and_set(key)

        def delete_model(key):
            if not messagebox.askyesno(
                "Delete Model",
                f"Delete the '{LOCAL_MODELS[key]['display']}' model files?\nYou can re-download it later.",
                parent=self._window
            ):
                return
            import shutil
            # Unload from memory FIRST so Windows releases file locks before we delete
            from voiceink.services.transcription import _model_cache
            if _model_cache._loaded_name == key:
                _model_cache.unload()
            deleted = False
            # Delete from manual MODELS_DIR
            local_path = MODELS_DIR / key
            if local_path.exists():
                shutil.rmtree(str(local_path), ignore_errors=True)
                deleted = True
            # Delete from HuggingFace disk cache directly
            folder = f"models--Systran--faster-whisper-{key}"
            import os as _os
            hf_hub_cache = _os.environ.get("HUGGINGFACE_HUB_CACHE")
            hf_home2 = _os.environ.get("HF_HOME")
            hf_candidates = []
            if hf_hub_cache:
                hf_candidates.append(Path(hf_hub_cache) / folder)
            elif hf_home2:
                hf_candidates.append(Path(hf_home2) / "hub" / folder)
            hf_candidates.append(Path.home() / ".cache" / "huggingface" / "hub" / folder)
            for cache_dir in hf_candidates:
                if cache_dir.exists():
                    shutil.rmtree(str(cache_dir), ignore_errors=True)
                    deleted = True
                    break
            if deleted:
                _downloaded.discard(key)
                # Find another downloaded model to fall back to (if any)
                fallback = next(
                    (k for k in LOCAL_MODELS if k != key and k in _downloaded),
                    None
                )
                if cur_key_var[0] == key:
                    cur_key_var[0] = fallback
                    if fallback:
                        self._settings.set("local_model_name", fallback)
                    else:
                        # No local models left — clear local selection
                        self._settings.set("local_model_name", "")
                _refresh_all_cards()
                _update_badge()
                messagebox.showinfo(
                    "Model Deleted",
                    f"'{LOCAL_MODELS[key]['display']}' has been deleted."
                    + ("" if fallback or cur_key_var[0] else
                       "\n\nNo local models remain. Download one or configure a Provider."),
                    parent=self._window
                )
            else:
                messagebox.showinfo("Delete Model", "No model files found to delete.", parent=self._window)

        stack_wrap = tk.Frame(lm_inner, bg=CONTENT_BG, padx=24)
        stack_wrap.pack(fill="x", pady=(0, 8))

        # ── Shared Parakeet state (must be before Whisper loop for set_default rebind) ──
        from voiceink.services.parakeet_transcription import PARAKEET_MODELS, check_model_downloaded

        _init_parakeet_provider = self._settings.get_str("transcription_provider")
        _init_parakeet_key = self._settings.get_str("parakeet_model_key") or ""
        cur_parakeet_key_var = [
            _init_parakeet_key if _init_parakeet_provider == "parakeet" else ""
        ]

        parakeet_downloading: set = set()
        parakeet_downloaded: set = set()
        for _pk in PARAKEET_MODELS:
            if check_model_downloaded(_pk):
                parakeet_downloaded.add(_pk)

        parakeet_card_registries: list = []

        def on_set_parakeet_default(key, backend):
            cur_parakeet_key_var[0] = key
            self._settings.set("parakeet_model_key", key)
            self._settings.set("parakeet_backend", backend)
            self._settings.set("transcription_provider", "parakeet")
            self._settings.set("local_model_name", "")
            cur_key_var[0] = None
            _refresh_all_cards()
            _update_badge()
            _refresh_all_parakeet_cards()

        def on_clear_parakeet():
            cur_parakeet_key_var[0] = ""
            self._settings.set("parakeet_model_key", "")
            self._settings.set("parakeet_backend", "")
            self._settings.set("transcription_provider", "local")
            _update_badge()

        def _refresh_all_parakeet_cards():
            """Recompute and update button/bg state for every Parakeet card."""
            from voiceink.services.parakeet_transcription import check_backend_available
            nemo_ok   = check_backend_available("nemo")
            onnx_ok   = check_backend_available("sherpa_onnx")
            hf_ok     = check_backend_available("transformers")
            backend_ok = {"nemo": nemo_ok, "sherpa_onnx": onnx_ok, "transformers": hf_ok}

            current = cur_parakeet_key_var[0]
            for registry in parakeet_card_registries:
                for key, cf, action_btn, del_btn, bg_widgets in registry:
                    meta    = PARAKEET_MODELS[key]
                    backend = meta["backend"]
                    deps    = backend_ok[backend]
                    is_sel  = (current == key)
                    is_dl   = key in parakeet_downloaded
                    in_prog = key in parakeet_downloading

                    bg     = ACCENT_LIGHT if is_sel else CARD_BG
                    border = ACCENT       if is_sel else CARD_BORDER
                    cf.configure(highlightbackground=border)
                    for w in bg_widgets:
                        try:
                            w.configure(bg=bg)
                        except Exception:
                            pass

                    if in_prog:
                        continue

                    if not deps:
                        action_btn.configure(text="Needs deps", state="disabled",
                                             bg=TEXT_MUTED, cursor="arrow")
                        del_btn.pack_forget()
                    elif is_sel:
                        action_btn.configure(text="Default", state="disabled",
                                             bg=SUCCESS, cursor="arrow")
                        if is_dl:
                            del_btn.pack(side="left", padx=(6, 0))
                    elif is_dl:
                        action_btn.configure(text="Set as Default", state="normal",
                                             bg=ACCENT, cursor="hand2",
                                             activebackground="#4F46E5")
                        del_btn.pack(side="left", padx=(6, 0))
                    else:
                        action_btn.configure(text="Download", state="normal",
                                             bg=ACCENT, cursor="hand2",
                                             activebackground="#4F46E5")
                        del_btn.pack_forget()

        # ── Parakeet refresh hook ────────────────────────────────────────────────
        _parakeet_refresh_hook: list = [None]

        # Rebind set_default so selecting a Whisper model also clears Parakeet selection
        _original_set_default = set_default
        def set_default(key):  # noqa: F811
            _original_set_default(key)
            cur_parakeet_key_var[0] = ""
            self._settings.set("parakeet_model_key", "")
            self._settings.set("parakeet_backend", "")
            if _parakeet_refresh_hook[0]:
                _parakeet_refresh_hook[0]()

        for key, meta in LOCAL_MODELS.items():
            is_selected = (key == cur_key_var[0])
            is_dl = key in _downloaded
            bg     = ACCENT_LIGHT if is_selected else CARD_BG
            border = ACCENT       if is_selected else CARD_BORDER

            cf = tk.Frame(stack_wrap, bg=bg, highlightthickness=1,
                          highlightbackground=border)
            cf.pack(fill="x", pady=4)
            model_card_frames[key] = cf

            inner_p = tk.Frame(cf, bg=bg, padx=14, pady=10)
            inner_p.pack(fill="x")

            # Left: info  |  Right: button
            left = tk.Frame(inner_p, bg=bg)
            left.pack(side="left", fill="x", expand=True)

            right = tk.Frame(inner_p, bg=bg)
            right.pack(side="right", padx=(8, 0))

            # Title
            title_row = tk.Frame(left, bg=bg)
            title_row.pack(fill="x")
            title_lbl = tk.Label(title_row, text=meta["display"], bg=bg, fg=HEADING,
                                 font=FONT_BOLD)
            title_lbl.pack(side="left")

            # Description
            desc_lbl = tk.Label(left, text=MODEL_DESCS.get(key, ""), bg=bg, fg=TEXT_MUTED,
                                font=FONT_SMALL, justify="left", anchor="w")
            desc_lbl.pack(anchor="w", pady=(2, 4))

            # Speed / Accuracy bars — bar dot frames are NOT added to bg_widgets
            bars_row = tk.Frame(left, bg=bg)
            bars_row.pack(anchor="w")
            bar_spacers = []
            bar_labels = []
            for bar_label, filled in [("Speed", SPEED_BARS[key]), ("Accuracy", ACC_BARS[key])]:
                lbl = tk.Label(bars_row, text=bar_label, bg=bg, fg=TEXT_MUTED,
                               font=FONT_SMALL, width=8, anchor="w")
                lbl.pack(side="left")
                bar_labels.append(lbl)
                for i in range(5):
                    # bar dots: fixed colors, intentionally excluded from bg_widgets
                    tk.Frame(bars_row, bg=ACCENT if i < filled else CARD_BORDER,
                             width=8, height=5).pack(side="left", padx=1)
                spacer = tk.Frame(bars_row, bg=bg, width=14)
                spacer.pack(side="left")
                bar_spacers.append(spacer)

            # Register all background-sensitive widgets (excludes bar dots)
            model_bg_widgets[key] = [
                cf, inner_p, left, right, title_row, title_lbl,
                desc_lbl, bars_row,
                *bar_labels, *bar_spacers,
            ]

            # Action button
            if is_selected:
                btn_text, btn_state, btn_cursor, btn_bg = "Default", "disabled", "arrow", SUCCESS
            elif is_dl:
                btn_text, btn_state, btn_cursor, btn_bg = "Set as Default", "normal", "hand2", ACCENT
            else:
                btn_text, btn_state, btn_cursor, btn_bg = "Download", "normal", "hand2", ACCENT

            # Horizontal row for action + delete buttons
            btn_wrap = tk.Frame(right, bg=bg)
            btn_wrap.pack(anchor="center")

            action_btn = tk.Button(btn_wrap, text=btn_text, bg=btn_bg, fg="white",
                                   relief="flat", bd=0, font=FONT_SMALL,
                                   cursor=btn_cursor, padx=10, pady=5,
                                   state=btn_state, activebackground="#4F46E5",
                                   activeforeground="white",
                                   command=lambda k=key: on_action_btn(k))
            action_btn.pack(side="left")
            model_action_btns[key] = action_btn

            # Delete button (icon, only shown when downloaded)
            del_btn = tk.Button(btn_wrap, text="\U0001f5d1", bg=ERROR, fg="white",
                                relief="flat", bd=0, font=("Segoe UI", 9),
                                cursor="hand2", padx=6, pady=5,
                                activebackground="#DC2626", activeforeground="white",
                                command=lambda k=key: delete_model(k))
            model_delete_btns[key] = del_btn
            if is_dl:
                del_btn.pack(side="left", padx=(6, 0))

            # Store btn_wrap so _refresh_all_cards can recolor it
            model_bg_widgets[key].append(btn_wrap)

        # ── Build Parakeet sections ────────────────────────────────────────────────
        nemo_registry, _ = self._build_parakeet_nemo_section(
            lm_inner, cur_parakeet_key_var, parakeet_downloaded, parakeet_downloading,
            on_set_parakeet_default, on_clear_parakeet, _refresh_all_parakeet_cards,
        )
        parakeet_card_registries.append(nemo_registry)

        comm_registry = self._build_parakeet_community_section(
            lm_inner, cur_parakeet_key_var, parakeet_downloaded, parakeet_downloading,
            on_set_parakeet_default, on_clear_parakeet, _refresh_all_parakeet_cards,
        )
        parakeet_card_registries.append(comm_registry)

        # Wire the hook now that _refresh_all_parakeet_cards is defined
        _parakeet_refresh_hook[0] = _refresh_all_parakeet_cards

        # Language & Prompt section
        self._section_label(lm_inner, "Language & Prompt")
        c3 = self._card(lm_inner)
        tk.Label(c3, text="Language", bg=CARD_BG, fg=TEXT,
                 font=FONT_BOLD).pack(anchor="w", pady=(0, 2))
        tk.Label(c3, text="auto = detect automatically", bg=CARD_BG,
                 fg=TEXT_MUTED, font=FONT_SMALL).pack(anchor="w", pady=(0, 4))
        lang_var = tk.StringVar(
            value=self._settings.get_str("transcription_language") or "auto")
        self._combobox(c3, lang_var,
                       ["auto","en","es","fr","de","zh","ja","ko","pt","it","ru","ar","hi"],
                       width=14).pack(anchor="w")
        lang_var.trace_add("write", lambda *_: self._settings.set(
            "transcription_language", lang_var.get()))

        tk.Frame(c3, bg=CARD_BG, height=10).pack()
        tk.Label(c3, text="Transcription Prompt", bg=CARD_BG, fg=TEXT,
                 font=FONT_BOLD).pack(anchor="w", pady=(0, 2))
        tk.Label(c3, text="Optional — improves accuracy for specific terms",
                 bg=CARD_BG, fg=TEXT_MUTED, font=FONT_SMALL).pack(anchor="w", pady=(0, 4))
        prompt_var = tk.StringVar(
            value=self._settings.get_str("transcription_prompt") or "")
        self._entry(c3, textvariable=prompt_var, width=44).pack(anchor="w", fill="x")
        prompt_var.trace_add("write", lambda *_: self._settings.set(
            "transcription_prompt", prompt_var.get()))

        tk.Frame(lm_inner, bg=CONTENT_BG, height=24).pack()

        # ── Provider tab ──────────────────────────────────────────────────────
        prov_frame = tk.Frame(tab_content, bg=CONTENT_BG)
        tab_frames["Provider"] = prov_frame

        pv_scroll_wrap = tk.Frame(prov_frame, bg=CONTENT_BG)
        pv_scroll_wrap.pack(fill="both", expand=True)
        pv_inner = self._make_scrollable(pv_scroll_wrap)

        TRANSCRIPTION_PROVIDERS = {
            "groq":     {"label": "Groq",                    "needs_key": True,  "needs_url": False, "model_fixed": "whisper-large-v3"},
            "openai":   {"label": "OpenAI",                  "needs_key": True,  "needs_url": False, "model_fixed": "whisper-1"},
            "deepgram": {"label": "Deepgram",                "needs_key": True,  "needs_url": False, "model_fixed": "nova-2"},
            "custom":   {"label": "Custom (OpenAI-compatible endpoint)", "needs_key": True, "needs_url": True, "model_fixed": None},
        }

        PROVIDER_DETAILS = {
            "groq":     ("Groq provides ultra-fast cloud transcription using Whisper Large v3.\n"
                         "Get your API key at console.groq.com"),
            "openai":   ("OpenAI Whisper API. Accurate and reliable cloud transcription.\n"
                         "Get your API key at platform.openai.com"),
            "deepgram": ("Deepgram Nova-2 offers real-time cloud transcription with high accuracy.\n"
                         "Get your API key at console.deepgram.com"),
            "custom":   ("Connect to any OpenAI-compatible transcription endpoint.\n"
                         "Provide the base URL, API key, and model name."),
        }

        PROVIDER_KEYS = {
            "groq":     "groq_transcription_api_key",
            "openai":   "openai_transcription_api_key",
            "deepgram": "deepgram_api_key",
            "custom":   "custom_transcription_api_key",
        }
        # Fall back to a shared key setting if provider-specific not stored yet
        def _get_prov_key(p):
            specific = self._settings.get_str(PROVIDER_KEYS.get(p, "")) or ""
            if not specific and p != "custom":
                return self._settings.get_str("transcription_api_key") or ""
            return specific

        self._section_label(pv_inner, "Active Transcription Provider")
        prov_card = self._card(pv_inner)

        _saved_prov = self._settings.get_str("transcription_provider") or "groq"
        if _saved_prov not in TRANSCRIPTION_PROVIDERS and _saved_prov != "parakeet":
            _saved_prov = "groq"
        # When saved provider is "parakeet", show "groq" in the cloud dropdown
        # (Parakeet is a local model, not a cloud provider — intentional)
        prov_var = tk.StringVar(value=_saved_prov if _saved_prov in TRANSCRIPTION_PROVIDERS else "groq")

        # Provider picker row
        picker_row = tk.Frame(prov_card, bg=CARD_BG)
        picker_row.pack(fill="x", pady=(0, 8))
        tk.Label(picker_row, text="Provider", bg=CARD_BG, fg=TEXT,
                 font=FONT_BOLD, width=14, anchor="w").pack(side="left")
        self._combobox(picker_row, prov_var,
                       list(TRANSCRIPTION_PROVIDERS.keys()),
                       width=28).pack(side="left")
        def _on_cloud_prov_change(*_):
            # Only write when the user is actively on the Provider tab — prevents
            # overwriting a "parakeet" provider just by switching to this tab
            if active_tab[0] == "Provider":
                self._settings.set("transcription_provider", prov_var.get())

        prov_var.trace_add("write", _on_cloud_prov_change)

        # Description label
        desc_lbl = tk.Label(prov_card, text="", bg=CARD_BG, fg=TEXT_MUTED,
                            font=FONT_SMALL, wraplength=560, justify="left", anchor="w")
        desc_lbl.pack(anchor="w", pady=(0, 4))

        # Dynamic fields section
        self._section_label(pv_inner, "Provider Settings")
        dyn_card = self._card(pv_inner)

        # API Key row
        key_row = tk.Frame(dyn_card, bg=CARD_BG)
        key_lbl_w = tk.Label(key_row, text="API Key", bg=CARD_BG, fg=TEXT,
                             font=FONT_BOLD, width=14, anchor="w")
        key_var = tk.StringVar()
        key_entry = self._entry(key_row, textvariable=key_var, show="\u2022", width=38)
        key_hint = tk.Label(dyn_card, text="", bg=CARD_BG, fg=TEXT_MUTED, font=FONT_SMALL)

        # Base URL row (custom only)
        url_row = tk.Frame(dyn_card, bg=CARD_BG)
        url_lbl_w = tk.Label(url_row, text="Base URL", bg=CARD_BG, fg=TEXT,
                             font=FONT_BOLD, width=14, anchor="w")
        url_var = tk.StringVar(
            value=self._settings.get_str("custom_transcription_base_url") or "")
        url_entry = self._entry(url_row, textvariable=url_var, width=38)
        url_var.trace_add("write", lambda *_: self._settings.set(
            "custom_transcription_base_url", url_var.get()))

        # Model row
        model_row = tk.Frame(dyn_card, bg=CARD_BG)
        model_lbl_w = tk.Label(model_row, text="Model", bg=CARD_BG, fg=TEXT,
                               font=FONT_BOLD, width=14, anchor="w")
        model_var2 = tk.StringVar(
            value=self._settings.get_str("custom_transcription_model") or "")
        model_entry = self._entry(model_row, textvariable=model_var2, width=28)
        model_hint = tk.Label(dyn_card, text="", bg=CARD_BG, fg=TEXT_MUTED, font=FONT_SMALL)
        model_var2.trace_add("write", lambda *_: self._settings.set(
            "custom_transcription_model", model_var2.get()))

        # Action buttons + feedback (defined before refresh_provider so they can be referenced)
        btn_row = tk.Frame(dyn_card, bg=CARD_BG)
        save_btn = tk.Button(btn_row, text="Save API Key", bg=ACCENT, fg="white",
                             relief="flat", bd=0, font=FONT_SMALL, cursor="hand2",
                             padx=12, pady=6, activebackground="#4F46E5",
                             activeforeground="white")
        save_btn.pack(side="left", padx=(0, 8))
        use_btn = tk.Button(btn_row, text="Use for Transcription", bg=SUCCESS, fg="white",
                            relief="flat", bd=0, font=FONT_SMALL, cursor="hand2",
                            padx=12, pady=6, activebackground="#15803D",
                            activeforeground="white")
        use_btn.pack(side="left")
        feedback_lbl = tk.Label(dyn_card, text="", bg=CARD_BG, fg=SUCCESS, font=FONT_SMALL)

        def _flash_feedback(msg, color=SUCCESS):
            feedback_lbl.configure(text=msg, fg=color)
            feedback_lbl.after(2500, lambda: feedback_lbl.configure(text=""))

        def save_key_action():
            p = prov_var.get()
            setting_key = PROVIDER_KEYS.get(p)
            if setting_key:
                self._settings.set(setting_key, key_var.get())
                self._settings.set("transcription_api_key", key_var.get())
            _flash_feedback("API key saved.")

        def use_for_transcription():
            p = prov_var.get()
            self._settings.set("transcription_provider", p)
            setting_key = PROVIDER_KEYS.get(p)
            if setting_key:
                self._settings.set(setting_key, key_var.get())
            # Deselect any local model card since a cloud provider is now active
            cur_key_var[0] = None
            _refresh_all_cards()
            _update_badge()
            labels = {"groq": "Groq", "openai": "OpenAI",
                      "deepgram": "Deepgram", "custom": "Custom"}
            _flash_feedback(f"{labels.get(p, p.title())} is now active for transcription.")

        save_btn.configure(command=save_key_action)
        use_btn.configure(command=use_for_transcription)

        def refresh_provider(*_):
            p = prov_var.get()
            cfg = TRANSCRIPTION_PROVIDERS.get(p, {})
            desc_lbl.configure(text=PROVIDER_DETAILS.get(p, ""))

            # Hide everything first
            for w in (key_row, key_hint, url_row, url_lbl_w, model_row, model_hint,
                      btn_row, feedback_lbl):
                w.pack_forget()

            # API key
            key_row.pack(fill="x", pady=(4, 2))
            key_lbl_w.pack(side="left")
            key_entry.pack(side="left")
            hints = {
                "groq":     "Get key at console.groq.com",
                "openai":   "Get key at platform.openai.com",
                "deepgram": "Get key at console.deepgram.com",
                "custom":   "API key for your endpoint",
            }
            key_hint.configure(text=hints.get(p, ""))
            key_hint.pack(anchor="w", pady=(0, 6))

            # Load saved key for this provider
            saved_key = _get_prov_key(p)
            key_var.set(saved_key)

            # Base URL (custom only)
            if cfg.get("needs_url"):
                url_row.pack(fill="x", pady=(4, 2))
                url_lbl_w.pack(side="left")
                url_entry.pack(side="left")

            # Model
            model_row.pack(fill="x", pady=(4, 2))
            model_lbl_w.pack(side="left")
            fixed = cfg.get("model_fixed")
            if fixed:
                model_var2.set(fixed)
                model_hint.configure(text=f"Fixed model: {fixed}")
            else:
                model_entry.pack(side="left")
                model_hint.configure(text="Enter the model/engine name for your endpoint")
            model_hint.pack(anchor="w", pady=(0, 8))

            btn_row.pack(fill="x", pady=(4, 2))
            feedback_lbl.pack(anchor="w", pady=(4, 0))

        prov_var.trace_add("write", refresh_provider)
        refresh_provider()

        tk.Frame(pv_inner, bg=CONTENT_BG, height=24).pack()

        # Activate first tab
        switch_tab("Local Model")
        return panel

    # ── AI Enhancement ────────────────────────────────────────────────────────

    def _build_ai_panel(self, parent):
        panel = tk.Frame(parent, bg=CONTENT_BG)
        self._panel_header(panel, "AI Enhancement",
                           "Post-process transcriptions with AI")

        scroll_wrap = tk.Frame(panel, bg=CONTENT_BG)
        scroll_wrap.pack(fill="both", expand=True)
        inner = self._make_scrollable(scroll_wrap)

        self._section_label(inner, "Enable")
        c = self._card(inner)
        en_var = tk.BooleanVar(value=self._settings.get_bool("ai_enhancement_enabled"))
        self._checkbox(c, "Enable AI Enhancement", en_var,
                       lambda: self._settings.set("ai_enhancement_enabled",
                                                   en_var.get())).pack(anchor="w")
        tk.Label(c, text="Transcriptions are polished by your chosen AI model when enabled.",
                 bg=CARD_BG, fg=TEXT_MUTED, font=FONT_SMALL,
                 wraplength=520, justify="left").pack(anchor="w", pady=(4, 0))

        self._section_label(inner, "Provider & Model")
        c2 = self._card(inner)
        tk.Label(c2, text="AI Provider", bg=CARD_BG, fg=TEXT,
                 font=FONT_BOLD).pack(anchor="w", pady=(0, 4))
        prov_var = tk.StringVar(value=self._settings.get_str("ai_provider") or "openai")
        self._combobox(c2, prov_var, list(PROVIDER_CONFIG.keys()),
                       width=20).pack(anchor="w")

        tk.Frame(c2, bg=CARD_BG, height=10).pack()
        tk.Label(c2, text="Model", bg=CARD_BG, fg=TEXT,
                 font=FONT_BOLD).pack(anchor="w", pady=(0, 2))
        tk.Label(c2, text="Leave blank for provider default",
                 bg=CARD_BG, fg=TEXT_MUTED, font=FONT_SMALL).pack(anchor="w", pady=(0, 4))
        model_var = tk.StringVar(value=self._settings.get_str("ai_model") or "")
        self._entry(c2, textvariable=model_var, width=30).pack(anchor="w")

        avail_lbl = tk.Label(c2, text="", bg=CARD_BG, fg=TEXT_MUTED,
                             font=FONT_SMALL, wraplength=480, justify="left")
        avail_lbl.pack(anchor="w", pady=(4, 0))

        def refresh_models(*_):
            models = AVAILABLE_MODELS.get(prov_var.get(), [])
            avail_lbl.configure(
                text=("Available: " + ", ".join(models)) if models
                else "(Dynamic — enter model name manually)")

        prov_var.trace_add("write", refresh_models)
        prov_var.trace_add("write", lambda *_: self._settings.set(
            "ai_provider", prov_var.get()))
        model_var.trace_add("write", lambda *_: self._settings.set(
            "ai_model", model_var.get()))
        refresh_models()

        self._section_label(inner, "API Key")
        c3 = self._card(inner)
        tk.Label(c3, text="API Key", bg=CARD_BG, fg=TEXT,
                 font=FONT_BOLD).pack(anchor="w", pady=(0, 4))
        key_var = tk.StringVar(value=self._settings.get_str("ai_api_key") or "")
        self._entry(c3, textvariable=key_var, show="\u2022",
                    width=40).pack(anchor="w", fill="x")
        key_var.trace_add("write", lambda *_: self._settings.set(
            "ai_api_key", key_var.get()))

        self._section_label(inner, "Ollama")
        c4 = self._card(inner)
        tk.Label(c4, text="Base URL", bg=CARD_BG, fg=TEXT,
                 font=FONT_BOLD).pack(anchor="w", pady=(0, 4))
        url_var = tk.StringVar(
            value=self._settings.get_str("ollama_base_url") or "http://localhost:11434")
        self._entry(c4, textvariable=url_var, width=36).pack(anchor="w")
        url_var.trace_add("write", lambda *_: self._settings.set(
            "ollama_base_url", url_var.get()))

        tk.Frame(c4, bg=CARD_BG, height=10).pack()
        tk.Label(c4, text="Ollama Model", bg=CARD_BG, fg=TEXT,
                 font=FONT_BOLD).pack(anchor="w", pady=(0, 4))
        om_var = tk.StringVar(value=self._settings.get_str("ollama_model") or "mistral")
        self._entry(c4, textvariable=om_var, width=24).pack(anchor="w")
        om_var.trace_add("write", lambda *_: self._settings.set(
            "ollama_model", om_var.get()))

        tk.Frame(inner, bg=CONTENT_BG, height=24).pack()
        return panel

    # ── Audio Input ───────────────────────────────────────────────────────────

    def _build_audio_panel(self, parent):
        panel = tk.Frame(parent, bg=CONTENT_BG)
        self._panel_header(panel, "Audio Input", "Microphone and audio settings")

        scroll_wrap = tk.Frame(panel, bg=CONTENT_BG)
        scroll_wrap.pack(fill="both", expand=True)
        inner = self._make_scrollable(scroll_wrap)

        self._section_label(inner, "Input Device")
        c = self._card(inner)

        recorder = AudioRecorder()
        devices  = recorder.get_devices()
        names    = ["System Default"] + [d["name"] for d in devices]
        indices  = [None] + [d["index"] for d in devices]
        cur_idx  = self._settings.get("input_device_index")
        try:
            cur_name = names[indices.index(cur_idx)]
        except (ValueError, IndexError):
            cur_name = "System Default"

        tk.Label(c, text="Microphone", bg=CARD_BG, fg=TEXT,
                 font=FONT_BOLD).pack(anchor="w", pady=(0, 4))
        dev_var = tk.StringVar(value=cur_name)
        self._combobox(c, dev_var, names, width=40).pack(anchor="w")

        def on_dev(*_):
            try:
                i = names.index(dev_var.get())
                self._settings.set("input_device_index", indices[i])
            except ValueError:
                self._settings.set("input_device_index", None)

        dev_var.trace_add("write", on_dev)

        self._section_label(inner, "Filler Words")
        c2 = self._card(inner)
        tk.Label(c2, text="Words to Remove", bg=CARD_BG, fg=TEXT,
                 font=FONT_BOLD).pack(anchor="w", pady=(0, 2))
        tk.Label(c2, text="One word or phrase per line",
                 bg=CARD_BG, fg=TEXT_MUTED, font=FONT_SMALL).pack(anchor="w", pady=(0, 6))
        existing = self._settings.get("filler_words") or []
        filler_txt = tk.Text(c2, bg=INPUT_BG, fg=TEXT, insertbackground=TEXT,
                             relief="flat", bd=0, font=FONT_SMALL, width=40, height=5,
                             highlightthickness=1, highlightbackground=INPUT_BORDER)
        filler_txt.insert("1.0", "\n".join(existing))
        filler_txt.pack(anchor="w", fill="x")

        def save_fillers():
            raw = filler_txt.get("1.0", "end").strip()
            self._settings.set("filler_words",
                               [w.strip() for w in raw.splitlines() if w.strip()])
            messagebox.showinfo("Saved", "Filler words saved.", parent=self._window)

        self._btn(c2, "Save Filler Words", save_fillers,
                  accent=True).pack(anchor="w", pady=(10, 0))

        tk.Frame(inner, bg=CONTENT_BG, height=24).pack()
        return panel

    # ── Hotkey ────────────────────────────────────────────────────────────────

    def _build_hotkey_panel(self, parent):
        panel = tk.Frame(parent, bg=CONTENT_BG)
        self._panel_header(panel, "Hotkey", "Configure the activation key")

        scroll_wrap = tk.Frame(panel, bg=CONTENT_BG)
        scroll_wrap.pack(fill="both", expand=True)
        inner = self._make_scrollable(scroll_wrap)

        self._section_label(inner, "Key")
        c = self._card(inner)
        tk.Label(c, text="Activation Key", bg=CARD_BG, fg=TEXT,
                 font=FONT_BOLD).pack(anchor="w", pady=(0, 4))
        key_var = tk.StringVar(
            value=self._settings.get_str("hotkey_key") or "right ctrl")
        self._combobox(c, key_var,
                       ["right ctrl","right alt","right shift","left ctrl","left alt",
                        "f9","f10","f11","f12","caps lock","scroll lock"],
                       width=22).pack(anchor="w")

        tk.Frame(c, bg=CARD_BG, height=8).pack()
        tk.Label(c, text="Custom Key Name", bg=CARD_BG, fg=TEXT,
                 font=FONT_BOLD).pack(anchor="w", pady=(0, 2))
        tk.Label(c, text="e.g.  f9 \u00b7 right ctrl \u00b7 caps lock",
                 bg=CARD_BG, fg=TEXT_MUTED, font=FONT_SMALL).pack(anchor="w", pady=(0, 4))
        self._entry(c, textvariable=key_var, width=22).pack(anchor="w")

        self._section_label(inner, "Mode")
        c2 = self._card(inner)
        tk.Label(c2, text="Activation Mode", bg=CARD_BG, fg=TEXT,
                 font=FONT_BOLD).pack(anchor="w", pady=(0, 4))
        mode_var = tk.StringVar(
            value=self._settings.get_str("hotkey_mode") or "hybrid")
        self._combobox(c2, mode_var,
                       ["toggle", "push_to_talk", "hybrid"],
                       width=22).pack(anchor="w")

        info = tk.Frame(c2, bg=ACCENT_LIGHT, padx=12, pady=10)
        info.pack(fill="x", pady=(10, 0))
        for mode, desc in [
            ("toggle",       "Press once to start, press again to stop"),
            ("push_to_talk", "Hold to record, release to stop"),
            ("hybrid",       "Short press = toggle, long press = push-to-talk"),
        ]:
            row = tk.Frame(info, bg=ACCENT_LIGHT)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=f"{mode}:", bg=ACCENT_LIGHT, fg=ACCENT,
                     font=FONT_BOLD, width=15, anchor="w").pack(side="left")
            tk.Label(row, text=desc, bg=ACCENT_LIGHT, fg=TEXT,
                     font=FONT_SMALL, anchor="w").pack(side="left")

        def save_hotkey():
            self._settings.set("hotkey_key", key_var.get().strip())
            self._settings.set("hotkey_mode", mode_var.get())
            if self._on_hotkey_change:
                self._on_hotkey_change()
            messagebox.showinfo("Saved", "Hotkey settings saved.",
                                parent=self._window)

        self._btn(c2, "Save Hotkey Settings", save_hotkey,
                  accent=True).pack(anchor="w", pady=(12, 0))

        tk.Frame(inner, bg=CONTENT_BG, height=24).pack()
        return panel

    # ── Prompts ───────────────────────────────────────────────────────────────

    def _build_prompts_panel(self, parent):
        panel = tk.Frame(parent, bg=CONTENT_BG)
        self._panel_header(panel, "Prompts", "Manage AI enhancement prompts")

        scroll_wrap = tk.Frame(panel, bg=CONTENT_BG)
        scroll_wrap.pack(fill="both", expand=True)
        inner = self._make_scrollable(scroll_wrap)

        self._section_label(inner, "Active Prompt")
        c = self._card(inner)
        tk.Label(c, text="Select the prompt used for AI enhancement",
                 bg=CARD_BG, fg=TEXT_MUTED, font=FONT_SMALL).pack(anchor="w", pady=(0, 8))
        list_frame = tk.Frame(c, bg=CARD_BG)
        list_frame.pack(fill="x")

        def rebuild_prompt_list():
            for w in list_frame.winfo_children():
                w.destroy()
            for p in prompt_store.prompts:
                is_active = self._settings.get("selected_prompt_id") == p.id
                row = tk.Frame(list_frame, bg=CARD_BG, highlightthickness=1,
                               highlightbackground=CARD_BORDER)
                row.pack(fill="x", pady=2)
                body = tk.Frame(row, bg=CARD_BG, padx=12, pady=8)
                body.pack(fill="x")
                left = tk.Frame(body, bg=CARD_BG)
                left.pack(side="left", fill="x", expand=True)

                def make_select(pid):
                    def _sel():
                        self._settings.set("selected_prompt_id", pid)
                        rebuild_prompt_list()
                    return _sel

                dot   = "\u25cf  " if is_active else "\u25cb  "
                color = ACCENT if is_active else TEXT_MUTED
                tk.Button(left, text=f"{dot}{p.title}",
                          bg=CARD_BG, fg=color, relief="flat", bd=0,
                          cursor="hand2",
                          font=FONT_BOLD if is_active else FONT,
                          command=make_select(p.id), anchor="w",
                          activebackground=CARD_BG,
                          activeforeground=ACCENT).pack(anchor="w")

                if not p.is_predefined:
                    def make_del(pid):
                        def _del():
                            prompt_store.delete(pid)
                            rebuild_prompt_list()
                        return _del
                    tk.Button(body, text="\u2715", bg=CARD_BG, fg=ERROR,
                              relief="flat", bd=0, cursor="hand2", font=FONT,
                              command=make_del(p.id),
                              activebackground=CARD_BG).pack(side="right")

        rebuild_prompt_list()

        self._section_label(inner, "Add Custom Prompt")
        c2 = self._card(inner)
        tk.Label(c2, text="Title", bg=CARD_BG, fg=TEXT,
                 font=FONT_BOLD).pack(anchor="w", pady=(0, 4))
        title_var = tk.StringVar()
        self._entry(c2, textvariable=title_var, width=40).pack(anchor="w", fill="x")

        tk.Frame(c2, bg=CARD_BG, height=10).pack()
        tk.Label(c2, text="Prompt Text", bg=CARD_BG, fg=TEXT,
                 font=FONT_BOLD).pack(anchor="w", pady=(0, 4))
        prompt_txt = tk.Text(c2, bg=INPUT_BG, fg=TEXT, insertbackground=TEXT,
                             relief="flat", bd=0, font=FONT_SMALL, width=46, height=5,
                             highlightthickness=1, highlightbackground=INPUT_BORDER)
        prompt_txt.pack(anchor="w", fill="x")

        tk.Frame(c2, bg=CARD_BG, height=8).pack()
        sys_var = tk.BooleanVar(value=True)
        self._checkbox(c2, "Include standard transcription instructions",
                       sys_var, lambda: None).pack(anchor="w", pady=2)

        def add_prompt():
            title = title_var.get().strip()
            text  = prompt_txt.get("1.0", "end").strip()
            if not title or not text:
                messagebox.showwarning("Missing fields",
                                       "Title and prompt text are required.",
                                       parent=self._window)
                return
            prompt_store.add(Prompt(
                id=str(uuid.uuid4()), title=title, prompt_text=text,
                use_system_instructions=sys_var.get()))
            title_var.set("")
            prompt_txt.delete("1.0", "end")
            rebuild_prompt_list()

        self._btn(c2, "Add Prompt", add_prompt,
                  accent=True).pack(anchor="w", pady=(10, 0))

        tk.Frame(inner, bg=CONTENT_BG, height=24).pack()
        return panel

    # ── General ───────────────────────────────────────────────────────────────

    def _build_general_panel(self, parent):
        panel = tk.Frame(parent, bg=CONTENT_BG)
        self._panel_header(panel, "General", "App-wide preferences")

        scroll_wrap = tk.Frame(panel, bg=CONTENT_BG)
        scroll_wrap.pack(fill="both", expand=True)
        inner = self._make_scrollable(scroll_wrap)

        self._section_label(inner, "Behaviour")
        c = self._card(inner)
        for text, key in [
            ("Auto-paste transcription at cursor",  "auto_paste"),
            ("Restore clipboard after paste",        "restore_clipboard"),
            ("Remove filler words (um, uh, like\u2026)", "filler_words_enabled"),
        ]:
            var = tk.BooleanVar(value=self._settings.get_bool(key))
            self._checkbox(c, text, var,
                           lambda k=key, v=var: self._settings.set(k, v.get())
                           ).pack(anchor="w", pady=2)

        self._section_label(inner, "Overlay Position")
        c2 = self._card(inner)
        tk.Label(c2, text="Recorder Overlay Position", bg=CARD_BG, fg=TEXT,
                 font=FONT_BOLD).pack(anchor="w", pady=(0, 4))
        pos_var = tk.StringVar(
            value=self._settings.get_str("recorder_position") or "bottom_right")
        self._combobox(c2, pos_var,
                       ["bottom_right","bottom_left","bottom_center",
                        "top_right","top_left","center"],
                       width=18).pack(anchor="w")
        pos_var.trace_add("write", lambda *_: self._settings.set(
            "recorder_position", pos_var.get()))

        self._section_label(inner, "Word Replacements")
        c3 = self._card(inner)
        tk.Label(c3, text="Automatic Word Replacements", bg=CARD_BG, fg=TEXT,
                 font=FONT_BOLD).pack(anchor="w", pady=(0, 2))
        tk.Label(c3, text="Format: one replacement per line,  FROM \u2192 TO",
                 bg=CARD_BG, fg=TEXT_MUTED, font=FONT_SMALL).pack(anchor="w", pady=(0, 6))
        existing = self._settings.get("word_replacements") or {}
        lines = [f"{k} \u2192 {v}" for k, v in existing.items()]
        repl_txt = tk.Text(c3, bg=INPUT_BG, fg=TEXT, insertbackground=TEXT,
                           relief="flat", bd=0, font=FONT_SMALL, width=46, height=6,
                           highlightthickness=1, highlightbackground=INPUT_BORDER)
        repl_txt.insert("1.0", "\n".join(lines))
        repl_txt.pack(anchor="w", fill="x")

        def save_replacements():
            raw    = repl_txt.get("1.0", "end").strip()
            result = {}
            for line in raw.splitlines():
                if "\u2192" in line:
                    src, _, dst = line.partition("\u2192")
                    if src.strip():
                        result[src.strip()] = dst.strip()
            self._settings.set("word_replacements", result)
            messagebox.showinfo("Saved", "Word replacements saved.",
                                parent=self._window)

        self._btn(c3, "Save Replacements", save_replacements,
                  accent=True).pack(anchor="w", pady=(10, 0))

        tk.Frame(inner, bg=CONTENT_BG, height=24).pack()
        return panel
