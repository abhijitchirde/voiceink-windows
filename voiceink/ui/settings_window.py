"""
Settings window — Windows equivalent of the Mac Settings views.
Tabbed interface covering: General, Transcription, AI Enhancement, Hotkey, Audio.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional
import threading

from voiceink.services.transcription import LOCAL_MODELS, MODELS_DIR
from voiceink.services.ai_enhancement import PROVIDER_CONFIG, AVAILABLE_MODELS
from voiceink.services.recorder import AudioRecorder
from voiceink.models.prompts import Prompt, prompt_store
from voiceink.models.transcription import store as transcription_store, TranscriptionRecord
import uuid

# ── Colours ──────────────────────────────────────────────────────────────────
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
FONT_HEAD  = ("Segoe UI", 13, "bold")


def _label(parent, text, muted=False, bold=False, **kw):
    colour = TEXT_MUTED if muted else TEXT
    font = FONT_BOLD if bold else FONT
    return tk.Label(parent, text=text, bg=parent["bg"], fg=colour, font=font, **kw)


def _entry(parent, textvariable=None, show=None, width=30):
    e = tk.Entry(
        parent, textvariable=textvariable, show=show,
        bg=BG3, fg=TEXT, insertbackground=TEXT,
        relief="flat", bd=0, font=FONT, width=width,
        highlightthickness=1, highlightcolor=ACCENT,
        highlightbackground=BORDER,
    )
    return e


def _combobox(parent, textvariable, values, width=28):
    style = ttk.Style()
    style.configure("Dark.TCombobox",
                    fieldbackground=BG3, background=BG3,
                    foreground=TEXT, selectbackground=ACCENT)
    cb = ttk.Combobox(
        parent, textvariable=textvariable,
        values=values, width=width,
        style="Dark.TCombobox", state="readonly",
    )
    return cb


def _button(parent, text, command, accent=False, **kw):
    bg = ACCENT if accent else BG3
    fg = "white" if accent else TEXT
    return tk.Button(
        parent, text=text, command=command,
        bg=bg, fg=fg, relief="flat", bd=0,
        font=FONT, cursor="hand2", padx=12, pady=6,
        activebackground=BG2, activeforeground=TEXT,
        **kw,
    )


def _separator(parent):
    tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", pady=8)


class SettingsWindow:
    def __init__(self, root: tk.Tk, settings, on_hotkey_change: Optional[Callable] = None):
        self._root = root
        self._settings = settings
        self._on_hotkey_change = on_hotkey_change
        self._window: Optional[tk.Toplevel] = None

    def show(self):
        if self._window and self._window.winfo_exists():
            self._window.lift()
            return
        self._build()

    def _build(self):
        w = tk.Toplevel(self._root)
        self._window = w
        w.title("VoiceInk Settings")
        w.configure(bg=BG)
        w.resizable(True, True)
        w.attributes("-topmost", False)
        w.geometry("860x620")

        # Notebook (tabs)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=BG2, foreground=TEXT_MUTED,
                        padding=[14, 6], font=FONT)
        style.map("TNotebook.Tab",
                  background=[("selected", BG3)],
                  foreground=[("selected", TEXT)])

        nb = ttk.Notebook(w)
        nb.pack(fill="both", expand=True, padx=0, pady=0)

        tabs = {
            "General":       self._build_general,
            "Hotkey":        self._build_hotkey,
            "Transcription": self._build_transcription,
            "AI":            self._build_ai,
            "Audio":         self._build_audio,
            "Prompts":       self._build_prompts,
            "History":       self._build_history,
        }
        for name, builder in tabs.items():
            frame = tk.Frame(nb, bg=BG, padx=20, pady=16)
            nb.add(frame, text=name)
            builder(frame)

        # Reload history whenever the History tab is selected
        def _on_tab_change(event):
            selected = nb.tab(nb.select(), "text")
            if selected == "History" and hasattr(self, "_history_reload"):
                self._history_reload()
        nb.bind("<<NotebookTabChanged>>", _on_tab_change)

    # ── General ──────────────────────────────────────────────────────────────

    def _build_general(self, frame):
        _label(frame, "General Settings", bold=True).pack(anchor="w", pady=(0, 12))

        auto_paste_var = tk.BooleanVar(value=self._settings.get_bool("auto_paste"))
        self._checkbox(frame, "Auto-paste transcription at cursor", auto_paste_var,
                       lambda: self._settings.set("auto_paste", auto_paste_var.get()))

        restore_var = tk.BooleanVar(value=self._settings.get_bool("restore_clipboard"))
        self._checkbox(frame, "Restore clipboard after paste", restore_var,
                       lambda: self._settings.set("restore_clipboard", restore_var.get()))

        filler_var = tk.BooleanVar(value=self._settings.get_bool("filler_words_enabled"))
        self._checkbox(frame, "Remove filler words (um, uh, like…)", filler_var,
                       lambda: self._settings.set("filler_words_enabled", filler_var.get()))

        _separator(frame)
        _label(frame, "Overlay Position", muted=True).pack(anchor="w")
        pos_var = tk.StringVar(value=self._settings.get_str("recorder_position") or "bottom_right")
        positions = ["bottom_right", "bottom_left", "bottom_center", "top_right", "top_left", "center"]
        cb = _combobox(frame, pos_var, positions, width=20)
        cb.pack(anchor="w", pady=(4, 0))
        pos_var.trace_add("write", lambda *_: self._settings.set("recorder_position", pos_var.get()))

        _separator(frame)
        _label(frame, "Word Replacements", bold=True).pack(anchor="w", pady=(0, 4))
        _label(frame, "Format: one replacement per line, FROM → TO", muted=True).pack(anchor="w")

        existing = self._settings.get("word_replacements") or {}
        lines = [f"{k} → {v}" for k, v in existing.items()]
        txt = tk.Text(frame, bg=BG3, fg=TEXT, insertbackground=TEXT,
                      relief="flat", bd=0, font=FONT_SMALL, width=46, height=6,
                      highlightthickness=1, highlightbackground=BORDER)
        txt.insert("1.0", "\n".join(lines))
        txt.pack(anchor="w", pady=(4, 0))

        def save_replacements():
            raw = txt.get("1.0", "end").strip()
            result = {}
            for line in raw.splitlines():
                if "→" in line:
                    parts = line.split("→", 1)
                    src, dst = parts[0].strip(), parts[1].strip()
                    if src:
                        result[src] = dst
            self._settings.set("word_replacements", result)
            messagebox.showinfo("Saved", "Word replacements saved.", parent=self._window)

        _button(frame, "Save Replacements", save_replacements).pack(anchor="w", pady=(6, 0))

    # ── Hotkey ────────────────────────────────────────────────────────────────

    def _build_hotkey(self, frame):
        _label(frame, "Hotkey Settings", bold=True).pack(anchor="w", pady=(0, 12))

        _label(frame, "Activation Key", muted=True).pack(anchor="w")
        key_var = tk.StringVar(value=self._settings.get_str("hotkey_key") or "right ctrl")
        common_keys = [
            "right ctrl", "right alt", "right shift",
            "left ctrl", "left alt",
            "f9", "f10", "f11", "f12",
            "caps lock", "scroll lock",
        ]
        cb = _combobox(frame, key_var, common_keys, width=24)
        cb.pack(anchor="w", pady=(4, 0))

        custom_key_entry = _entry(frame, textvariable=key_var, width=24)
        custom_key_entry.pack(anchor="w", pady=(4, 0))
        _label(frame, "Type any key name (e.g. f9, right ctrl, caps lock)", muted=True).pack(anchor="w")

        _separator(frame)
        _label(frame, "Activation Mode", muted=True).pack(anchor="w")
        mode_var = tk.StringVar(value=self._settings.get_str("hotkey_mode") or "hybrid")
        modes = ["toggle", "push_to_talk", "hybrid"]
        mode_cb = _combobox(frame, mode_var, modes, width=24)
        mode_cb.pack(anchor="w", pady=(4, 0))

        _label(frame,
               "toggle: press once to start, again to stop\n"
               "push_to_talk: hold to record, release to stop\n"
               "hybrid: short press = toggle, long press = push-to-talk",
               muted=True).pack(anchor="w", pady=(4, 0))

        def save_hotkey():
            self._settings.set("hotkey_key", key_var.get().strip())
            self._settings.set("hotkey_mode", mode_var.get())
            if self._on_hotkey_change:
                self._on_hotkey_change()
            messagebox.showinfo("Saved", "Hotkey settings saved. Reload app if needed.",
                                parent=self._window)

        _button(frame, "Save Hotkey", save_hotkey, accent=True).pack(anchor="w", pady=(12, 0))

    # ── Transcription ────────────────────────────────────────────────────────

    def _build_transcription(self, frame):
        _label(frame, "Transcription Settings", bold=True).pack(anchor="w", pady=(0, 12))

        _label(frame, "Provider", muted=True).pack(anchor="w")
        provider_var = tk.StringVar(value=self._settings.get_str("transcription_provider") or "local")
        providers = ["local", "groq", "openai", "deepgram", "custom"]
        _combobox(frame, provider_var, providers, width=20).pack(anchor="w", pady=(4, 0))
        provider_var.trace_add("write", lambda *_: self._settings.set("transcription_provider", provider_var.get()))

        _separator(frame)
        _label(frame, "Local Model (faster-whisper)", muted=True).pack(anchor="w")
        model_display = {v["display"]: k for k, v in LOCAL_MODELS.items()}
        current_model = self._settings.get_str("local_model_name") or "base"
        current_display = LOCAL_MODELS.get(current_model, {}).get("display", current_model)
        model_var = tk.StringVar(value=current_display)
        model_names = [v["display"] for v in LOCAL_MODELS.values()]
        _combobox(frame, model_var, model_names, width=24).pack(anchor="w", pady=(4, 0))

        def on_model_change(*_):
            key = model_display.get(model_var.get(), "base")
            self._settings.set("local_model_name", key)

        model_var.trace_add("write", on_model_change)

        download_status = tk.Label(frame, text="", bg=BG, fg=TEXT_MUTED, font=FONT_SMALL)
        download_status.pack(anchor="w", pady=(2, 0))

        def download_model():
            key = model_display.get(model_var.get(), "base")
            model_dir = MODELS_DIR / key
            if model_dir.exists():
                download_status.configure(text=f"Model '{key}' already downloaded.", fg=SUCCESS)
                return
            download_status.configure(text=f"Downloading '{key}' — this may take a few minutes...", fg=TEXT_MUTED)

            def _do():
                try:
                    from faster_whisper import WhisperModel
                    WhisperModel(key, device="cpu", compute_type="int8")
                    download_status.configure(text=f"'{key}' downloaded successfully.", fg=SUCCESS)
                except Exception as e:
                    download_status.configure(text=f"Download failed: {e}", fg=ERROR)

            threading.Thread(target=_do, daemon=True).start()

        _button(frame, "Download Selected Model", download_model).pack(anchor="w", pady=(6, 0))

        _separator(frame)
        _label(frame, "Language (auto = detect automatically)", muted=True).pack(anchor="w")
        lang_var = tk.StringVar(value=self._settings.get_str("transcription_language") or "auto")
        langs = ["auto", "en", "es", "fr", "de", "zh", "ja", "ko", "pt", "it", "ru", "ar", "hi"]
        _combobox(frame, lang_var, langs, width=16).pack(anchor="w", pady=(4, 0))
        lang_var.trace_add("write", lambda *_: self._settings.set("transcription_language", lang_var.get()))

        _separator(frame)
        _label(frame, "Transcription Prompt (optional, improves accuracy)", muted=True).pack(anchor="w")
        prompt_var = tk.StringVar(value=self._settings.get_str("transcription_prompt") or "")
        _entry(frame, textvariable=prompt_var, width=46).pack(anchor="w", pady=(4, 0))
        prompt_var.trace_add("write", lambda *_: self._settings.set("transcription_prompt", prompt_var.get()))

    # ── AI Enhancement ───────────────────────────────────────────────────────

    def _build_ai(self, frame):
        _label(frame, "AI Enhancement", bold=True).pack(anchor="w", pady=(0, 12))

        enabled_var = tk.BooleanVar(value=self._settings.get_bool("ai_enhancement_enabled"))
        self._checkbox(frame, "Enable AI Enhancement", enabled_var,
                       lambda: self._settings.set("ai_enhancement_enabled", enabled_var.get()))

        _separator(frame)
        _label(frame, "AI Provider", muted=True).pack(anchor="w")
        provider_var = tk.StringVar(value=self._settings.get_str("ai_provider") or "openai")
        ai_providers = list(PROVIDER_CONFIG.keys())
        provider_cb = _combobox(frame, provider_var, ai_providers, width=20)
        provider_cb.pack(anchor="w", pady=(4, 0))

        _label(frame, "Model (leave blank for provider default)", muted=True).pack(anchor="w", pady=(8, 0))
        model_var = tk.StringVar(value=self._settings.get_str("ai_model") or "")
        model_entry = _entry(frame, textvariable=model_var, width=30)
        model_entry.pack(anchor="w", pady=(4, 0))

        available_label = tk.Label(frame, text="", bg=BG, fg=TEXT_MUTED, font=FONT_SMALL, wraplength=480, justify="left")
        available_label.pack(anchor="w", pady=(2, 0))

        def refresh_models(*_):
            prov = provider_var.get()
            models = AVAILABLE_MODELS.get(prov, [])
            if models:
                available_label.configure(text="Available: " + ", ".join(models))
            else:
                available_label.configure(text="(Dynamic — enter model name manually)")

        provider_var.trace_add("write", refresh_models)
        provider_var.trace_add("write", lambda *_: self._settings.set("ai_provider", provider_var.get()))
        model_var.trace_add("write", lambda *_: self._settings.set("ai_model", model_var.get()))
        refresh_models()

        _separator(frame)
        _label(frame, "API Key", muted=True).pack(anchor="w")
        key_var = tk.StringVar(value=self._settings.get_str("ai_api_key") or "")
        key_entry = _entry(frame, textvariable=key_var, show="•", width=40)
        key_entry.pack(anchor="w", pady=(4, 0))
        key_var.trace_add("write", lambda *_: self._settings.set("ai_api_key", key_var.get()))

        _separator(frame)
        _label(frame, "Ollama Settings (if using Ollama)", muted=True).pack(anchor="w")
        ollama_url_var = tk.StringVar(value=self._settings.get_str("ollama_base_url") or "http://localhost:11434")
        _label(frame, "Base URL:", muted=True).pack(anchor="w", pady=(4, 0))
        _entry(frame, textvariable=ollama_url_var, width=36).pack(anchor="w")
        ollama_url_var.trace_add("write", lambda *_: self._settings.set("ollama_base_url", ollama_url_var.get()))

        ollama_model_var = tk.StringVar(value=self._settings.get_str("ollama_model") or "mistral")
        _label(frame, "Model:", muted=True).pack(anchor="w", pady=(4, 0))
        _entry(frame, textvariable=ollama_model_var, width=24).pack(anchor="w")
        ollama_model_var.trace_add("write", lambda *_: self._settings.set("ollama_model", ollama_model_var.get()))

    # ── Audio ────────────────────────────────────────────────────────────────

    def _build_audio(self, frame):
        _label(frame, "Audio Input", bold=True).pack(anchor="w", pady=(0, 12))

        recorder = AudioRecorder()
        devices = recorder.get_devices()
        device_names = ["System Default"] + [d["name"] for d in devices]
        device_indices = [None] + [d["index"] for d in devices]

        current_idx = self._settings.get("input_device_index")
        try:
            current_name = device_names[device_indices.index(current_idx)]
        except (ValueError, IndexError):
            current_name = "System Default"

        device_var = tk.StringVar(value=current_name)
        _label(frame, "Input Device", muted=True).pack(anchor="w")
        _combobox(frame, device_var, device_names, width=40).pack(anchor="w", pady=(4, 0))

        def on_device_change(*_):
            name = device_var.get()
            try:
                idx = device_names.index(name)
                self._settings.set("input_device_index", device_indices[idx])
            except ValueError:
                self._settings.set("input_device_index", None)

        device_var.trace_add("write", on_device_change)

        _separator(frame)
        _label(frame, "Filler Words to Remove", muted=True).pack(anchor="w")
        existing_fillers = self._settings.get("filler_words") or []
        filler_txt = tk.Text(frame, bg=BG3, fg=TEXT, insertbackground=TEXT,
                             relief="flat", bd=0, font=FONT_SMALL, width=40, height=4,
                             highlightthickness=1, highlightbackground=BORDER)
        filler_txt.insert("1.0", "\n".join(existing_fillers))
        filler_txt.pack(anchor="w", pady=(4, 0))
        _label(frame, "One word/phrase per line", muted=True).pack(anchor="w")

        def save_fillers():
            raw = filler_txt.get("1.0", "end").strip()
            words = [w.strip() for w in raw.splitlines() if w.strip()]
            self._settings.set("filler_words", words)
            messagebox.showinfo("Saved", "Filler words saved.", parent=self._window)

        _button(frame, "Save Filler Words", save_fillers).pack(anchor="w", pady=(6, 0))

    # ── Prompts ───────────────────────────────────────────────────────────────

    def _build_prompts(self, frame):
        _label(frame, "AI Prompts", bold=True).pack(anchor="w", pady=(0, 8))
        _label(frame, "Select the active prompt used for AI enhancement.",
               muted=True).pack(anchor="w", pady=(0, 8))

        selected_id = self._settings.get("selected_prompt_id")

        list_frame = tk.Frame(frame, bg=BG2, padx=8, pady=8)
        list_frame.pack(fill="x")

        def rebuild_prompt_list():
            for w in list_frame.winfo_children():
                w.destroy()
            for p in prompt_store.prompts:
                row = tk.Frame(list_frame, bg=BG2)
                row.pack(fill="x", pady=2)
                is_active = (self._settings.get("selected_prompt_id") == p.id)
                dot = "●" if is_active else "○"
                colour = ACCENT if is_active else TEXT_MUTED

                def make_select(pid):
                    def _select():
                        self._settings.set("selected_prompt_id", pid)
                        rebuild_prompt_list()
                    return _select

                tk.Button(row, text=f"{dot}  {p.title}", bg=BG2, fg=colour,
                          relief="flat", bd=0, cursor="hand2", font=FONT,
                          command=make_select(p.id), anchor="w",
                          activebackground=BG3, activeforeground=TEXT,
                          ).pack(side="left", fill="x", expand=True)

                if not p.is_predefined:
                    def make_delete(pid):
                        def _delete():
                            prompt_store.delete(pid)
                            rebuild_prompt_list()
                        return _delete
                    tk.Button(row, text="✕", bg=BG2, fg=ERROR, relief="flat",
                              bd=0, cursor="hand2", font=FONT,
                              command=make_delete(p.id),
                              activebackground=BG3).pack(side="right")

        rebuild_prompt_list()

        _separator(frame)
        _label(frame, "Add Custom Prompt", bold=True).pack(anchor="w", pady=(0, 4))

        title_var = tk.StringVar()
        _label(frame, "Title:", muted=True).pack(anchor="w")
        _entry(frame, textvariable=title_var, width=40).pack(anchor="w", pady=(2, 0))

        _label(frame, "Prompt text:", muted=True).pack(anchor="w", pady=(6, 0))
        prompt_txt = tk.Text(frame, bg=BG3, fg=TEXT, insertbackground=TEXT,
                             relief="flat", bd=0, font=FONT_SMALL, width=46, height=5,
                             highlightthickness=1, highlightbackground=BORDER)
        prompt_txt.pack(anchor="w", pady=(2, 0))

        sys_var = tk.BooleanVar(value=True)
        self._checkbox(frame, "Include standard transcription instructions", sys_var, lambda: None)

        def add_prompt():
            title = title_var.get().strip()
            text = prompt_txt.get("1.0", "end").strip()
            if not title or not text:
                messagebox.showwarning("Missing fields", "Title and prompt text are required.",
                                       parent=self._window)
                return
            p = Prompt(
                id=str(uuid.uuid4()),
                title=title,
                prompt_text=text,
                use_system_instructions=sys_var.get(),
            )
            prompt_store.add(p)
            title_var.set("")
            prompt_txt.delete("1.0", "end")
            rebuild_prompt_list()

        _button(frame, "Add Prompt", add_prompt, accent=True).pack(anchor="w", pady=(6, 0))

    # ── History ───────────────────────────────────────────────────────────────

    def _build_history(self, frame):
        """Embed the full transcription history UI inside the History tab."""
        from tkinter import messagebox as _mb

        # State
        records: list = []
        filtered: list = []
        selected_idx: list = [None]  # mutable container

        frame.configure(padx=0, pady=0)  # let children fill edge-to-edge

        # ── Top bar ──────────────────────────────────────────────────────────
        top = tk.Frame(frame, bg=BG2, padx=12, pady=8)
        top.pack(fill="x")

        tk.Label(top, text="Transcription History", bg=BG2, fg=TEXT,
                 font=FONT_HEAD).pack(side="left")

        clear_btn = tk.Button(
            top, text="Clear All", bg=ERROR, fg="white", relief="flat", bd=0,
            font=FONT, cursor="hand2", padx=10, pady=4,
            activebackground="#dc2626",
        )
        clear_btn.pack(side="right", padx=(0, 16))

        search_var = tk.StringVar()
        search_entry = tk.Entry(
            top, textvariable=search_var, bg=BG3, fg=TEXT,
            insertbackground=TEXT, relief="flat", bd=0, font=FONT, width=26,
            highlightthickness=1, highlightcolor=ACCENT, highlightbackground=BORDER,
        )
        search_entry.pack(side="right", padx=(8, 0))
        tk.Label(top, text="Search:", bg=BG2, fg=TEXT_MUTED, font=FONT).pack(side="right")

        # ── Left/right pane ──────────────────────────────────────────────────
        pane = tk.PanedWindow(frame, orient="horizontal", bg=BORDER, sashwidth=2,
                              sashrelief="flat")
        pane.pack(fill="both", expand=True)

        list_frame = tk.Frame(pane, bg=BG, width=300)
        pane.add(list_frame, minsize=200)

        listbox = tk.Listbox(
            list_frame, bg=BG, fg=TEXT, selectbackground=BG3,
            selectforeground=ACCENT, relief="flat", bd=0, font=FONT_SMALL,
            activestyle="none", highlightthickness=0,
        )
        sb_list = ttk.Scrollbar(list_frame, orient="vertical", command=listbox.yview)
        listbox.configure(yscrollcommand=sb_list.set)
        sb_list.pack(side="right", fill="y")
        listbox.pack(fill="both", expand=True)

        # ── Detail panel ─────────────────────────────────────────────────────
        detail_frame = tk.Frame(pane, bg=BG)
        pane.add(detail_frame, minsize=380)

        detail_top = tk.Frame(detail_frame, bg=BG, padx=12, pady=8)
        detail_top.pack(fill="x")

        meta_label = tk.Label(detail_top, text="", bg=BG, fg=TEXT_MUTED,
                              font=FONT_SMALL, justify="left", anchor="w")
        meta_label.pack(side="left", fill="x", expand=True)

        btn_frame = tk.Frame(detail_top, bg=BG)
        btn_frame.pack(side="right")

        # Raw / Enhanced sub-tabs
        style = ttk.Style()
        style.configure("Detail.TNotebook", background=BG, borderwidth=0)
        style.configure("Detail.TNotebook.Tab", background=BG2, foreground=TEXT_MUTED,
                        padding=[10, 4], font=FONT_SMALL)
        style.map("Detail.TNotebook.Tab",
                  background=[("selected", BG3)],
                  foreground=[("selected", TEXT)])

        detail_nb = ttk.Notebook(detail_frame, style="Detail.TNotebook")
        detail_nb.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        raw_frame = tk.Frame(detail_nb, bg=BG3)
        detail_nb.add(raw_frame, text="Raw Transcription")
        raw_text = tk.Text(raw_frame, bg=BG3, fg=TEXT, insertbackground=TEXT,
                           relief="flat", bd=8, font=FONT_SMALL, wrap="word",
                           state="disabled", highlightthickness=0)
        raw_sb = ttk.Scrollbar(raw_frame, orient="vertical", command=raw_text.yview)
        raw_text.configure(yscrollcommand=raw_sb.set)
        raw_sb.pack(side="right", fill="y")
        raw_text.pack(fill="both", expand=True)

        enh_frame = tk.Frame(detail_nb, bg=BG3)
        detail_nb.add(enh_frame, text="Enhanced")
        enh_text = tk.Text(enh_frame, bg=BG3, fg=TEXT, insertbackground=TEXT,
                           relief="flat", bd=8, font=FONT_SMALL, wrap="word",
                           state="disabled", highlightthickness=0)
        enh_sb = ttk.Scrollbar(enh_frame, orient="vertical", command=enh_text.yview)
        enh_text.configure(yscrollcommand=enh_sb.set)
        enh_sb.pack(side="right", fill="y")
        enh_text.pack(fill="both", expand=True)

        # ── Logic helpers ─────────────────────────────────────────────────────

        def current_record():
            idx = selected_idx[0]
            if idx is not None and idx < len(filtered):
                return filtered[idx]
            return None

        def rebuild_list():
            listbox.delete(0, "end")
            for r in filtered:
                ts = r.timestamp.strftime("%m/%d %H:%M")
                preview = r.text[:50].replace("\n", " ")
                if len(r.text) > 50:
                    preview += "…"
                listbox.insert("end", f"  {ts}  {preview}")

        def apply_filter(*_):
            query = search_var.get().lower().strip()
            if query:
                filtered[:] = [
                    r for r in records
                    if query in r.text.lower()
                    or (r.enhanced_text and query in r.enhanced_text.lower())
                ]
            else:
                filtered[:] = list(records)
            rebuild_list()

        def reload():
            records[:] = transcription_store.get_all(limit=500)
            selected_idx[0] = None
            apply_filter()

        # Store reload so tab-change event can call it
        self._history_reload = reload

        def show_detail(record):
            ts = record.timestamp.strftime("%A, %B %d %Y at %H:%M:%S")
            duration = f"{record.duration:.1f}s"
            model = record.transcription_model or "unknown"
            meta = f"{ts}  |  Duration: {duration}  |  Model: {model}"
            if record.ai_model:
                meta += f"  |  AI: {record.ai_model}"
            meta_label.configure(text=meta)

            raw_text.configure(state="normal")
            raw_text.delete("1.0", "end")
            raw_text.insert("1.0", record.text)
            raw_text.configure(state="disabled")

            enh_text.configure(state="normal")
            enh_text.delete("1.0", "end")
            enh_text.insert("1.0", record.enhanced_text or "(No AI enhancement for this entry)")
            enh_text.configure(state="disabled")

        def on_select(event):
            sel = listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            if idx >= len(filtered):
                return
            selected_idx[0] = idx
            show_detail(filtered[idx])

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
            if not r:
                return
            if _mb.askyesno("Delete", "Delete this transcription?", parent=self._window):
                transcription_store.delete(r.id)
                selected_idx[0] = None
                meta_label.configure(text="")
                raw_text.configure(state="normal")
                raw_text.delete("1.0", "end")
                raw_text.configure(state="disabled")
                enh_text.configure(state="normal")
                enh_text.delete("1.0", "end")
                enh_text.configure(state="disabled")
                reload()

        def clear_all():
            if _mb.askyesno("Clear All",
                            "Delete ALL transcription history? This cannot be undone.",
                            parent=self._window):
                transcription_store.delete_all()
                reload()

        # ── Wire up events ────────────────────────────────────────────────────
        listbox.bind("<<ListboxSelect>>", on_select)
        search_var.trace_add("write", apply_filter)
        clear_btn.configure(command=clear_all)

        tk.Button(btn_frame, text="Copy Raw", bg=BG3, fg=TEXT, relief="flat", bd=0,
                  font=FONT_SMALL, cursor="hand2", padx=8, pady=4,
                  command=copy_raw,
                  activebackground=BG2).pack(side="left", padx=2)
        tk.Button(btn_frame, text="Copy Enhanced", bg=ACCENT, fg="white",
                  relief="flat", bd=0, font=FONT_SMALL, cursor="hand2", padx=8, pady=4,
                  command=copy_enhanced,
                  activebackground="#4f46e5").pack(side="left", padx=2)
        tk.Button(btn_frame, text="Delete", bg=BG3, fg=ERROR, relief="flat", bd=0,
                  font=FONT_SMALL, cursor="hand2", padx=8, pady=4,
                  command=delete_selected,
                  activebackground=BG2).pack(side="left", padx=2)

        reload()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _checkbox(self, parent, text, variable, command):
        def _toggle():
            command()
        cb = tk.Checkbutton(
            parent, text=text, variable=variable,
            bg=parent["bg"], fg=TEXT, selectcolor=BG3,
            activebackground=parent["bg"], activeforeground=TEXT,
            font=FONT, command=_toggle,
        )
        cb.pack(anchor="w", pady=2)
        return cb
