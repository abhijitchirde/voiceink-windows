"""
Persistent settings store — mirrors UserDefaults from the Mac version.
All settings are saved to a JSON file in the user's AppData folder.
"""

import json
import os
from pathlib import Path
from typing import Any, Optional


def _settings_path() -> Path:
    app_data = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    directory = app_data / "VoiceInk"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "settings.json"


_DEFAULTS: dict[str, Any] = {
    # Hotkey
    "hotkey_key": "right ctrl",
    "hotkey_mode": "hybrid",           # toggle | push_to_talk | hybrid
    "hotkey_hybrid_threshold": 0.5,

    # Transcription
    "transcription_provider": "local",  # local | groq | deepgram | openai | custom
    "local_model_name": "base",         # tiny | base | small | medium | large-v3
    "transcription_language": "auto",
    "transcription_prompt": "",
    "transcription_api_key": "",        # legacy shared key
    "groq_transcription_api_key": "",
    "openai_transcription_api_key": "",
    "deepgram_api_key": "",
    "custom_transcription_api_key": "",
    "custom_transcription_base_url": "",
    "custom_transcription_model": "",

    # AI Enhancement
    "ai_enhancement_enabled": False,
    "ai_provider": "openai",           # openai | anthropic | groq | gemini | ollama | custom
    "ai_model": "",                    # empty = use provider default
    "ai_api_key": "",
    "ollama_base_url": "http://localhost:11434",
    "ollama_model": "mistral",
    "custom_ai_base_url": "",
    "custom_ai_model": "",
    "selected_prompt_id": None,

    # Paste behaviour
    "auto_paste": True,
    "restore_clipboard": True,
    "clipboard_restore_delay": 0.3,

    # Audio
    "input_device_index": None,        # None = system default

    # Word replacements
    "word_replacements": {},           # {"from": "to", ...}

    # Filler words
    "filler_words_enabled": True,
    "filler_words": ["um", "uh", "like", "you know", "sort of", "kind of"],

    # UI
    "launch_at_startup": False,
    "show_in_taskbar": False,
    "recorder_position": "bottom_right",  # bottom_right | bottom_left | bottom_center | top_right | top_left | center

    # History
    "history_max_items": 500,
    "auto_cleanup_days": 30,

    # Parakeet local models
    "parakeet_model_key": "",   # e.g. "parakeet-nemo-110m" — empty = none selected
    "parakeet_backend":   "",   # "nemo" | "sherpa_onnx" | "transformers" — empty = none
}


class Settings:
    """Thread-safe settings store backed by a JSON file."""

    def __init__(self):
        self._path = _settings_path()
        self._data: dict[str, Any] = dict(_DEFAULTS)
        self._load()

    def _load(self):
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self._data.update(saved)
            except Exception:
                pass  # corrupt file — use defaults

    def save(self):
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, _DEFAULTS.get(key, default))

    def set(self, key: str, value: Any):
        self._data[key] = value
        self.save()

    def reset(self, key: str):
        self._data[key] = _DEFAULTS.get(key)
        self.save()

    def reset_all(self):
        self._data = dict(_DEFAULTS)
        self.save()

    # Convenience typed accessors
    def get_str(self, key: str) -> str:
        return str(self.get(key, ""))

    def get_bool(self, key: str) -> bool:
        return bool(self.get(key, False))

    def get_int(self, key: str) -> int:
        return int(self.get(key, 0))

    def get_float(self, key: str) -> float:
        return float(self.get(key, 0.0))


# Module-level singleton
settings = Settings()
