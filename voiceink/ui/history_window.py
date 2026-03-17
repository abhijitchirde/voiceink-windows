"""
Transcription history window — Windows equivalent of HistoryWindowController.swift.
Shows all past transcriptions with copy, delete, and search.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional
from datetime import datetime

from voiceink.models.transcription import store as transcription_store, TranscriptionRecord

BG         = "#1e1e2e"
BG2        = "#2a2a3e"
BG3        = "#313147"
ACCENT     = "#6366f1"
TEXT       = "#e2e8f0"
TEXT_MUTED = "#94a3b8"
BORDER     = "#3f3f60"
ERROR      = "#ef4444"
SUCCESS    = "#22c55e"
FONT       = ("Segoe UI", 10)
FONT_BOLD  = ("Segoe UI", 10, "bold")
FONT_SMALL = ("Segoe UI", 9)
FONT_MONO  = ("Consolas", 9)


class HistoryWindow:
    def __init__(self, root: tk.Tk):
        self._root = root
        self._window: Optional[tk.Toplevel] = None
        self._records: list[TranscriptionRecord] = []
        self._filtered: list[TranscriptionRecord] = []
        self._selected_idx: Optional[int] = None

    def show(self):
        if self._window and self._window.winfo_exists():
            self._window.lift()
            self._reload()
            return
        self._build()

    def _build(self):
        w = tk.Toplevel(self._root)
        self._window = w
        w.title("Transcription History — VoiceInk")
        w.configure(bg=BG)
        w.geometry("860x560")
        w.minsize(640, 400)

        # ── Top bar ──────────────────────────────────────────────────────────
        top = tk.Frame(w, bg=BG2, padx=12, pady=8)
        top.pack(fill="x")

        tk.Label(top, text="History", bg=BG2, fg=TEXT,
                 font=("Segoe UI", 13, "bold")).pack(side="left")

        # Search
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._apply_filter())
        search_entry = tk.Entry(
            top, textvariable=self._search_var, bg=BG3, fg=TEXT,
            insertbackground=TEXT, relief="flat", bd=0, font=FONT, width=28,
            highlightthickness=1, highlightcolor=ACCENT, highlightbackground=BORDER,
        )
        search_entry.pack(side="right", padx=(8, 0))
        tk.Label(top, text="Search:", bg=BG2, fg=TEXT_MUTED, font=FONT).pack(side="right")

        clear_btn = tk.Button(
            top, text="Clear All", bg=ERROR, fg="white", relief="flat", bd=0,
            font=FONT, cursor="hand2", padx=10, pady=4,
            command=self._clear_all,
            activebackground="#dc2626",
        )
        clear_btn.pack(side="right", padx=(0, 16))

        # ── Main pane ────────────────────────────────────────────────────────
        pane = tk.PanedWindow(w, orient="horizontal", bg=BORDER, sashwidth=2,
                              sashrelief="flat")
        pane.pack(fill="both", expand=True)

        # List panel
        list_frame = tk.Frame(pane, bg=BG, width=320)
        pane.add(list_frame, minsize=220)

        self._listbox = tk.Listbox(
            list_frame, bg=BG, fg=TEXT, selectbackground=BG3,
            selectforeground=ACCENT, relief="flat", bd=0, font=FONT_SMALL,
            activestyle="none", highlightthickness=0,
        )
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical",
                                  command=self._listbox.yview)
        self._listbox.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._listbox.pack(fill="both", expand=True)
        self._listbox.bind("<<ListboxSelect>>", self._on_select)

        # Detail panel
        detail_frame = tk.Frame(pane, bg=BG)
        pane.add(detail_frame, minsize=360)

        detail_top = tk.Frame(detail_frame, bg=BG, padx=12, pady=8)
        detail_top.pack(fill="x")

        self._meta_label = tk.Label(detail_top, text="", bg=BG, fg=TEXT_MUTED,
                                    font=FONT_SMALL, justify="left", anchor="w")
        self._meta_label.pack(side="left", fill="x", expand=True)

        btn_frame = tk.Frame(detail_top, bg=BG)
        btn_frame.pack(side="right")

        tk.Button(btn_frame, text="Copy Raw", bg=BG3, fg=TEXT, relief="flat", bd=0,
                  font=FONT_SMALL, cursor="hand2", padx=8, pady=4,
                  command=self._copy_raw,
                  activebackground=BG2).pack(side="left", padx=2)

        tk.Button(btn_frame, text="Copy Enhanced", bg=ACCENT, fg="white",
                  relief="flat", bd=0, font=FONT_SMALL, cursor="hand2", padx=8, pady=4,
                  command=self._copy_enhanced,
                  activebackground="#4f46e5").pack(side="left", padx=2)

        tk.Button(btn_frame, text="Delete", bg=BG3, fg=ERROR, relief="flat", bd=0,
                  font=FONT_SMALL, cursor="hand2", padx=8, pady=4,
                  command=self._delete_selected,
                  activebackground=BG2).pack(side="left", padx=2)

        # Tabs for raw / enhanced
        style = ttk.Style()
        style.configure("Detail.TNotebook", background=BG, borderwidth=0)
        style.configure("Detail.TNotebook.Tab", background=BG2, foreground=TEXT_MUTED,
                        padding=[10, 4], font=FONT_SMALL)
        style.map("Detail.TNotebook.Tab",
                  background=[("selected", BG3)],
                  foreground=[("selected", TEXT)])

        nb = ttk.Notebook(detail_frame, style="Detail.TNotebook")
        nb.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        raw_frame = tk.Frame(nb, bg=BG3)
        nb.add(raw_frame, text="Raw Transcription")
        self._raw_text = tk.Text(
            raw_frame, bg=BG3, fg=TEXT, insertbackground=TEXT,
            relief="flat", bd=8, font=FONT_MONO, wrap="word",
            state="disabled", highlightthickness=0,
        )
        raw_sb = ttk.Scrollbar(raw_frame, orient="vertical", command=self._raw_text.yview)
        self._raw_text.configure(yscrollcommand=raw_sb.set)
        raw_sb.pack(side="right", fill="y")
        self._raw_text.pack(fill="both", expand=True)

        enhanced_frame = tk.Frame(nb, bg=BG3)
        nb.add(enhanced_frame, text="Enhanced")
        self._enhanced_text = tk.Text(
            enhanced_frame, bg=BG3, fg=TEXT, insertbackground=TEXT,
            relief="flat", bd=8, font=FONT_MONO, wrap="word",
            state="disabled", highlightthickness=0,
        )
        enh_sb = ttk.Scrollbar(enhanced_frame, orient="vertical",
                               command=self._enhanced_text.yview)
        self._enhanced_text.configure(yscrollcommand=enh_sb.set)
        enh_sb.pack(side="right", fill="y")
        self._enhanced_text.pack(fill="both", expand=True)

        self._reload()

    # ------------------------------------------------------------------

    def _reload(self):
        self._records = transcription_store.get_all(limit=500)
        self._apply_filter()

    def _apply_filter(self):
        query = self._search_var.get().lower().strip() if hasattr(self, "_search_var") else ""
        if query:
            self._filtered = [
                r for r in self._records
                if query in r.text.lower()
                or (r.enhanced_text and query in r.enhanced_text.lower())
            ]
        else:
            self._filtered = list(self._records)
        self._rebuild_list()

    def _rebuild_list(self):
        self._listbox.delete(0, "end")
        for r in self._filtered:
            ts = r.timestamp.strftime("%m/%d %H:%M")
            preview = r.text[:50].replace("\n", " ")
            if len(r.text) > 50:
                preview += "…"
            self._listbox.insert("end", f"  {ts}  {preview}")

    def _on_select(self, event):
        sel = self._listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self._filtered):
            return
        record = self._filtered[idx]
        self._selected_idx = idx
        self._show_detail(record)

    def _show_detail(self, record: TranscriptionRecord):
        # Meta
        ts = record.timestamp.strftime("%A, %B %d %Y at %H:%M:%S")
        duration = f"{record.duration:.1f}s"
        model = record.transcription_model or "unknown"
        meta = f"{ts}  |  Duration: {duration}  |  Model: {model}"
        if record.ai_model:
            meta += f"  |  AI: {record.ai_model}"
        self._meta_label.configure(text=meta)

        # Raw text
        self._raw_text.configure(state="normal")
        self._raw_text.delete("1.0", "end")
        self._raw_text.insert("1.0", record.text)
        self._raw_text.configure(state="disabled")

        # Enhanced text
        self._enhanced_text.configure(state="normal")
        self._enhanced_text.delete("1.0", "end")
        if record.enhanced_text:
            self._enhanced_text.insert("1.0", record.enhanced_text)
        else:
            self._enhanced_text.insert("1.0", "(No AI enhancement for this entry)")
        self._enhanced_text.configure(state="disabled")

    def _current_record(self) -> Optional[TranscriptionRecord]:
        if self._selected_idx is not None and self._selected_idx < len(self._filtered):
            return self._filtered[self._selected_idx]
        return None

    def _copy_raw(self):
        record = self._current_record()
        if record:
            self._root.clipboard_clear()
            self._root.clipboard_append(record.text)

    def _copy_enhanced(self):
        record = self._current_record()
        if record:
            text = record.enhanced_text or record.text
            self._root.clipboard_clear()
            self._root.clipboard_append(text)

    def _delete_selected(self):
        record = self._current_record()
        if not record:
            return
        if messagebox.askyesno("Delete", "Delete this transcription?",
                               parent=self._window):
            transcription_store.delete(record.id)
            self._selected_idx = None
            self._reload()
            self._meta_label.configure(text="")
            self._raw_text.configure(state="normal")
            self._raw_text.delete("1.0", "end")
            self._raw_text.configure(state="disabled")
            self._enhanced_text.configure(state="normal")
            self._enhanced_text.delete("1.0", "end")
            self._enhanced_text.configure(state="disabled")

    def _clear_all(self):
        if messagebox.askyesno("Clear All", "Delete ALL transcription history? This cannot be undone.",
                               parent=self._window):
            transcription_store.delete_all()
            self._reload()
