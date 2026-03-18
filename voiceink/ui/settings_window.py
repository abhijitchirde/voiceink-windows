"""
Settings window — sidebar navigation, light mode, flat design.
Mirrors the macOS VoiceInk layout: left nav + right content panel.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional
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
    ("\u25ce", "Transcription"),
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
        w = tk.Toplevel(self._root)
        self._window = w
        w.title("VoiceInk Settings")
        w.configure(bg=CONTENT_BG)
        w.resizable(True, True)
        w.attributes("-topmost", False)
        w.geometry("960x640")
        w.minsize(800, 540)
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
        self._panels["Transcription"]  = self._build_transcription_panel(self._content_area)
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

        # Help & Resources
        self._section_label(inner, "Help & Resources")
        links = [
            ("\u229e", "Documentation",      "Read the VoiceInk docs and guides"),
            ("\u25ce", "Feedback or Issues?", "Report a bug or request a feature"),
        ]
        for icon, title, desc in links:
            row_wrap = tk.Frame(inner, bg=CONTENT_BG, padx=24)
            row_wrap.pack(fill="x", pady=3)
            card = tk.Frame(row_wrap, bg=CARD_BG, highlightthickness=1,
                            highlightbackground=CARD_BORDER, cursor="hand2")
            card.pack(fill="x")
            body = tk.Frame(card, bg=CARD_BG, padx=14, pady=12)
            body.pack(fill="x")
            left = tk.Frame(body, bg=CARD_BG)
            left.pack(side="left", fill="x", expand=True)
            tk.Label(left, text=f"{icon}  {title}", bg=CARD_BG, fg=HEADING,
                     font=FONT_BOLD).pack(anchor="w")
            tk.Label(left, text=desc, bg=CARD_BG, fg=TEXT_MUTED,
                     font=FONT_SMALL).pack(anchor="w")
            tk.Label(body, text="\u2197", bg=CARD_BG, fg=TEXT_MUTED,
                     font=("Segoe UI", 12)).pack(side="right")

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

        list_outer = tk.Frame(pane, bg=CONTENT_BG, width=280)
        pane.add(list_outer, minsize=200)

        listbox = tk.Listbox(list_outer, bg=CONTENT_BG, fg=TEXT,
                             selectbackground=ACCENT_LIGHT,
                             selectforeground=ACCENT,
                             relief="flat", bd=0, font=FONT_SMALL,
                             activestyle="none", highlightthickness=0)
        list_sb = ttk.Scrollbar(list_outer, orient="vertical",
                                command=listbox.yview,
                                style="Light.Vertical.TScrollbar")
        listbox.configure(yscrollcommand=list_sb.set)
        list_sb.pack(side="right", fill="y")
        listbox.pack(fill="both", expand=True)

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

        def rebuild_list():
            listbox.delete(0, "end")
            for r in filtered:
                ts = r.timestamp.strftime("%m/%d %H:%M")
                preview = r.text[:50].replace("\n", " ")
                listbox.insert("end", f"  {ts}  {preview}{'…' if len(r.text) > 50 else ''}")

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

        def on_select(_):
            sel = listbox.curselection()
            if sel and sel[0] < len(filtered):
                selected_idx[0] = sel[0]
                show_detail(filtered[sel[0]])

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

        listbox.bind("<<ListboxSelect>>", on_select)
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

    def _build_transcription_panel(self, parent):
        panel = tk.Frame(parent, bg=CONTENT_BG)
        self._panel_header(panel, "Transcription", "Speech-to-text settings")

        scroll_wrap = tk.Frame(panel, bg=CONTENT_BG)
        scroll_wrap.pack(fill="both", expand=True)
        inner = self._make_scrollable(scroll_wrap)

        self._section_label(inner, "Provider")
        c = self._card(inner)
        tk.Label(c, text="Transcription Provider", bg=CARD_BG, fg=TEXT,
                 font=FONT_BOLD).pack(anchor="w", pady=(0, 4))
        prov_var = tk.StringVar(
            value=self._settings.get_str("transcription_provider") or "local")
        self._combobox(c, prov_var,
                       ["local", "groq", "openai", "deepgram", "custom"],
                       width=20).pack(anchor="w")
        prov_var.trace_add("write", lambda *_: self._settings.set(
            "transcription_provider", prov_var.get()))

        self._section_label(inner, "Local Model")
        c2 = self._card(inner)
        tk.Label(c2, text="Model (faster-whisper)", bg=CARD_BG, fg=TEXT,
                 font=FONT_BOLD).pack(anchor="w", pady=(0, 4))
        display_map = {v["display"]: k for k, v in LOCAL_MODELS.items()}
        cur_key  = self._settings.get_str("local_model_name") or "base"
        cur_disp = LOCAL_MODELS.get(cur_key, {}).get("display", cur_key)
        model_var = tk.StringVar(value=cur_disp)
        self._combobox(c2, model_var,
                       [v["display"] for v in LOCAL_MODELS.values()],
                       width=24).pack(anchor="w")
        model_var.trace_add("write", lambda *_: self._settings.set(
            "local_model_name", display_map.get(model_var.get(), "base")))

        dl_status = tk.Label(c2, text="", bg=CARD_BG, fg=TEXT_MUTED, font=FONT_SMALL)
        dl_status.pack(anchor="w", pady=(6, 0))

        def download_model():
            key = display_map.get(model_var.get(), "base")
            if (MODELS_DIR / key).exists():
                dl_status.configure(text=f"\u2713 '{key}' already downloaded.", fg=SUCCESS)
                return
            dl_status.configure(text=f"Downloading '{key}'...", fg=TEXT_MUTED)
            def _do():
                try:
                    from faster_whisper import WhisperModel
                    WhisperModel(key, device="cpu", compute_type="int8")
                    dl_status.configure(text=f"\u2713 '{key}' downloaded.", fg=SUCCESS)
                except Exception as e:
                    dl_status.configure(text=f"\u2715 Failed: {e}", fg=ERROR)
            threading.Thread(target=_do, daemon=True).start()

        self._btn(c2, "Download Selected Model", download_model,
                  accent=True).pack(anchor="w", pady=(8, 0))

        self._section_label(inner, "Language & Prompt")
        c3 = self._card(inner)
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

        tk.Frame(inner, bg=CONTENT_BG, height=24).pack()
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
