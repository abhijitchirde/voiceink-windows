# NVIDIA Parakeet Models Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a comprehensive NVIDIA Parakeet speech-to-text section to the Local Model tab in VoiceInk's AI Models settings panel, supporting 10 models across NeMo, sherpa-onnx, and HF Transformers backends with full download/select/delete UI and one-click dependency installation.

**Architecture:** A new `parakeet_transcription.py` service module handles all backend detection, model download, caching, and inference — completely isolated from the existing Whisper `transcription.py`. The settings window gets two new sub-sections (NeMo and Community) inserted below the Whisper cards, reusing every existing UI helper (`_card`, `_section_label`, dot-bars, button patterns). `TranscriptionService` gets a thin dispatch branch, `engine.py` gets a one-line history fix, and `settings.py` gets two new default keys.

**Tech Stack:** Python 3.10+, tkinter, huggingface_hub (snapshot_download), nemo_toolkit[asr] (optional/lazy), sherpa-onnx (optional/lazy), transformers>=4.47 + torch + torchaudio (optional/lazy), subprocess (pip install), threading

**Spec:** `docs/superpowers/specs/2026-03-19-parakeet-models-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `voiceink/services/parakeet_transcription.py` | **Create** | PARAKEET_MODELS dict, backend detection, download, cache, inference |
| `voiceink/models/settings.py` | Modify | Add `parakeet_model_key` and `parakeet_backend` to `_DEFAULTS` |
| `voiceink/services/transcription.py` | Modify | Add `parakeet` provider dispatch + `_transcribe_parakeet()` wrapper |
| `voiceink/services/engine.py` | Modify | Fix history model name recording for `parakeet` provider |
| `voiceink/ui/settings_window.py` | Modify | Add two Parakeet UI sections, update badge, fix Provider tab guard |
| `requirements.txt` | Modify | Add commented optional Parakeet dep lines |
| `tests/test_parakeet_transcription.py` | **Create** | Unit tests for backend detection, model catalogue, download detection |

---

## Task 1: Add `parakeet_model_key` and `parakeet_backend` to Settings

**Files:**
- Modify: `voiceink/models/settings.py:19-72`

- [ ] **Step 1.1: Write the failing test**

Create `tests/test_parakeet_transcription.py`:

```python
"""Tests for Parakeet settings defaults and service module."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from voiceink.models.settings import _DEFAULTS


def test_parakeet_settings_defaults_exist():
    assert "parakeet_model_key" in _DEFAULTS
    assert "parakeet_backend" in _DEFAULTS


def test_parakeet_settings_defaults_are_empty_strings():
    assert _DEFAULTS["parakeet_model_key"] == ""
    assert _DEFAULTS["parakeet_backend"] == ""
```

- [ ] **Step 1.2: Run to verify it fails**

```bash
cd d:/Development/voiceink-windows
python -m pytest tests/test_parakeet_transcription.py::test_parakeet_settings_defaults_exist -v
```

Expected: `FAILED — KeyError or AssertionError`

- [ ] **Step 1.3: Add the defaults to settings.py**

In `voiceink/models/settings.py`, inside `_DEFAULTS` dict after the `"history_max_items"` / `"auto_cleanup_days"` block, add:

```python
    # Parakeet local models
    "parakeet_model_key": "",   # e.g. "parakeet-nemo-110m" — empty = none selected
    "parakeet_backend":   "",   # "nemo" | "sherpa_onnx" | "transformers" — empty = none
```

- [ ] **Step 1.4: Run tests to verify they pass**

```bash
python -m pytest tests/test_parakeet_transcription.py -v
```

Expected: `2 passed`

- [ ] **Step 1.5: Commit**

```bash
git add voiceink/models/settings.py tests/test_parakeet_transcription.py
git commit -m "feat: add parakeet_model_key and parakeet_backend settings defaults"
```

---

## Task 2: Create `parakeet_transcription.py` — Model Catalogue and Backend Detection

**Files:**
- Create: `voiceink/services/parakeet_transcription.py`

- [ ] **Step 2.1: Write failing tests for model catalogue and backend detection**

Append to `tests/test_parakeet_transcription.py`:

```python
from voiceink.services.parakeet_transcription import (
    PARAKEET_MODELS,
    check_backend_available,
    check_cuda_available,
    check_model_downloaded,
    MODELS_DIR_PARAKEET,
)


def test_parakeet_models_catalogue_has_10_entries():
    assert len(PARAKEET_MODELS) == 10


def test_parakeet_models_all_have_required_keys():
    required = {"display", "hf_repo", "size_mb", "language", "speed", "accuracy",
                "backend", "description", "cuda_badge"}
    for key, meta in PARAKEET_MODELS.items():
        missing = required - meta.keys()
        assert not missing, f"Model '{key}' missing keys: {missing}"


def test_parakeet_models_backends_are_valid():
    valid_backends = {"nemo", "sherpa_onnx", "transformers"}
    for key, meta in PARAKEET_MODELS.items():
        assert meta["backend"] in valid_backends, f"'{key}' has invalid backend '{meta['backend']}'"


def test_nemo_models_count():
    nemo = [k for k, m in PARAKEET_MODELS.items() if m["backend"] == "nemo"]
    assert len(nemo) == 4


def test_sherpa_onnx_models_count():
    onnx = [k for k, m in PARAKEET_MODELS.items() if m["backend"] == "sherpa_onnx"]
    assert len(onnx) == 4


def test_transformers_models_count():
    hf = [k for k, m in PARAKEET_MODELS.items() if m["backend"] == "transformers"]
    assert len(hf) == 2


def test_check_backend_available_returns_bool_for_missing():
    # "bogus_backend" should return False, not raise
    result = check_backend_available("bogus_backend")
    assert result is False


def test_check_cuda_available_returns_bool():
    result = check_cuda_available()
    assert isinstance(result, bool)


def test_check_model_downloaded_returns_false_for_nonexistent_key():
    result = check_model_downloaded("parakeet-nemo-110m")
    # Model won't be downloaded in test env — should be False, not raise
    assert result is False


def test_models_dir_parakeet_is_path():
    from pathlib import Path
    assert isinstance(MODELS_DIR_PARAKEET, Path)
```

- [ ] **Step 2.2: Run to verify they fail**

```bash
python -m pytest tests/test_parakeet_transcription.py -v
```

Expected: `ImportError` — module doesn't exist yet

- [ ] **Step 2.3: Create `voiceink/services/parakeet_transcription.py`**

```python
"""
Parakeet transcription service — NeMo, sherpa-onnx, and HF Transformers backends.
All backend imports are lazy (try/except) so the app starts even if none are installed.
"""

import os
import threading
import wave
from pathlib import Path
from typing import Any, Callable, Optional

from voiceink.services.transcription import MODELS_DIR

MODELS_DIR_PARAKEET = MODELS_DIR / "parakeet"

# ── Model catalogue ───────────────────────────────────────────────────────────

PARAKEET_MODELS: dict[str, dict] = {
    # ── NeMo backend ─────────────────────────────────────────────────────────
    "parakeet-nemo-110m": {
        "display":     "Parakeet 110M",
        "hf_repo":     "nvidia/parakeet-tdt_ctc-110m",
        "size_mb":     459,
        "language":    "English",
        "speed":       4,
        "accuracy":    3,
        "backend":     "nemo",
        "quantization": None,
        "cuda_badge":  None,
        "description": "Smallest NeMo Parakeet model (114M params). Fastest on CPU, "
                       "good for quick transcriptions. English only.",
    },
    "parakeet-nemo-0.6b-v2": {
        "display":     "Parakeet TDT 0.6B v2",
        "hf_repo":     "nvidia/parakeet-tdt-0.6b-v2",
        "size_mb":     2470,
        "language":    "English",
        "speed":       3,
        "accuracy":    4,
        "backend":     "nemo",
        "quantization": None,
        "cuda_badge":  "recommended",
        "description": "NVIDIA Parakeet 0.6B v2. Excellent English accuracy with "
                       "word-level timestamps. CUDA GPU strongly recommended.",
    },
    "parakeet-nemo-0.6b-v3": {
        "display":     "Parakeet TDT 0.6B v3",
        "hf_repo":     "nvidia/parakeet-tdt-0.6b-v3",
        "size_mb":     2510,
        "language":    "25 languages",
        "speed":       3,
        "accuracy":    4,
        "backend":     "nemo",
        "quantization": None,
        "cuda_badge":  "recommended",
        "description": "Parakeet 0.6B v3 — multilingual support for English and "
                       "25 European languages. CUDA GPU strongly recommended.",
    },
    "parakeet-nemo-1.1b": {
        "display":     "Parakeet TDT 1.1B",
        "hf_repo":     "nvidia/parakeet-tdt-1.1b",
        "size_mb":     4280,
        "language":    "English",
        "speed":       2,
        "accuracy":    5,
        "backend":     "nemo",
        "quantization": None,
        "cuda_badge":  "required",
        "description": "Highest accuracy NeMo Parakeet model. Requires CUDA GPU — "
                       "will be extremely slow on CPU-only systems.",
    },
    # ── sherpa-onnx backend ───────────────────────────────────────────────────
    "parakeet-onnx-0.6b-v2-int8": {
        "display":     "Parakeet 0.6B v2 INT8",
        "hf_repo":     "csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8",
        "size_mb":     661,
        "language":    "English",
        "speed":       3,
        "accuracy":    3,
        "backend":     "sherpa_onnx",
        "quantization": "INT8",
        "cuda_badge":  None,
        "description": "Community INT8-quantized Parakeet 0.6B v2. No PyTorch needed. "
                       "Great CPU performance, ~661 MB.",
    },
    "parakeet-onnx-0.6b-v2-fp16": {
        "display":     "Parakeet 0.6B v2 FP16",
        "hf_repo":     "csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-fp16",
        "size_mb":     1200,
        "language":    "English",
        "speed":       3,
        "accuracy":    4,
        "backend":     "sherpa_onnx",
        "quantization": "FP16",
        "cuda_badge":  None,
        "description": "Community FP16 Parakeet 0.6B v2. Better accuracy than INT8, "
                       "still no PyTorch needed.",
    },
    "parakeet-onnx-0.6b-v3-int8": {
        "display":     "Parakeet 0.6B v3 INT8",
        "hf_repo":     "csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8",
        "size_mb":     661,
        "language":    "25 languages",
        "speed":       3,
        "accuracy":    3,
        "backend":     "sherpa_onnx",
        "quantization": "INT8",
        "cuda_badge":  None,
        "description": "Community INT8-quantized Parakeet 0.6B v3. Multilingual, "
                       "25 European languages. No PyTorch needed.",
    },
    "parakeet-onnx-0.6b-v3-fp16": {
        "display":     "Parakeet 0.6B v3 FP16",
        "hf_repo":     "csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-fp16",
        "size_mb":     1200,
        "language":    "25 languages",
        "speed":       3,
        "accuracy":    4,
        "backend":     "sherpa_onnx",
        "quantization": "FP16",
        "cuda_badge":  None,
        "description": "Community FP16 Parakeet 0.6B v3. Best community multilingual "
                       "option — no PyTorch needed.",
    },
    # ── HF Transformers backend ───────────────────────────────────────────────
    "parakeet-hf-ctc-0.6b": {
        "display":     "Parakeet CTC 0.6B",
        "hf_repo":     "nvidia/parakeet-ctc-0.6b",
        "size_mb":     2300,
        "language":    "English",
        "speed":       3,
        "accuracy":    4,
        "backend":     "transformers",
        "quantization": None,
        "cuda_badge":  None,
        "description": "Official NVIDIA CTC 0.6B via HuggingFace Transformers. "
                       "Requires transformers>=4.47, torch, torchaudio.",
    },
    "parakeet-hf-ctc-1.1b": {
        "display":     "Parakeet CTC 1.1B",
        "hf_repo":     "nvidia/parakeet-ctc-1.1b",
        "size_mb":     4300,
        "language":    "English",
        "speed":       2,
        "accuracy":    5,
        "backend":     "transformers",
        "quantization": None,
        "cuda_badge":  None,
        "description": "Official NVIDIA CTC 1.1B via HuggingFace Transformers. "
                       "Highest CTC accuracy. Requires transformers>=4.47, torch, torchaudio.",
    },
}

# ── Pip install commands per backend ─────────────────────────────────────────

BACKEND_PIP_CMDS: dict[str, list[str]] = {
    "nemo":         ["nemo_toolkit[asr]", "torch"],
    "sherpa_onnx":  ["sherpa-onnx"],
    "transformers": ["transformers>=4.47.0", "torch", "torchaudio"],
}


# ── Backend detection ─────────────────────────────────────────────────────────

def check_backend_available(backend: str) -> bool:
    """Safe import-check. Returns False on any error — never raises."""
    try:
        if backend == "nemo":
            import nemo.collections.asr  # noqa: F401
            return True
        elif backend == "sherpa_onnx":
            import sherpa_onnx  # noqa: F401
            return True
        elif backend == "transformers":
            # importlib.metadata is stdlib in Python 3.8+; no extra deps needed
            import importlib.metadata
            import transformers  # noqa: F401
            ver = importlib.metadata.version("transformers")
            parts = ver.split(".")
            major, minor = int(parts[0]), int(parts[1])
            return (major, minor) >= (4, 47)
        return False
    except Exception:
        return False


def check_cuda_available() -> bool:
    """Returns torch.cuda.is_available(), or False if torch not installed."""
    try:
        import torch
        return bool(torch.cuda.is_available())
    except Exception:
        return False


def check_model_downloaded(key: str) -> bool:
    """Check whether model files are present on disk for this key."""
    if key not in PARAKEET_MODELS:
        return False
    meta = PARAKEET_MODELS[key]
    model_dir = MODELS_DIR_PARAKEET / key
    if not model_dir.exists():
        return False
    backend = meta["backend"]
    if backend == "nemo":
        return any(model_dir.glob("*.nemo"))
    elif backend == "sherpa_onnx":
        return (model_dir / "tokens.txt").exists() and any(model_dir.glob("*.onnx"))
    elif backend == "transformers":
        return (model_dir / "config.json").exists()
    return False


# ── Model cache ───────────────────────────────────────────────────────────────

class ParakeetModelCache:
    """Keeps the last-used Parakeet model in memory. Thread-safe.
    Must call unload() before deleting model files (Windows file lock requirement)."""

    def __init__(self):
        self._model = None
        self._loaded_key: Optional[str] = None
        self._lock = threading.Lock()

    def get(self, key: str, backend: str) -> Any:
        with self._lock:
            if self._model is not None and self._loaded_key == key:
                return self._model
            self._load(key, backend)
            return self._model

    def _load(self, key: str, backend: str):
        meta = PARAKEET_MODELS[key]
        model_dir = MODELS_DIR_PARAKEET / key
        cuda = check_cuda_available()

        if backend == "nemo":
            import nemo.collections.asr as nemo_asr
            import torch
            nemo_files = sorted(model_dir.glob("*.nemo"),
                                key=lambda p: p.stat().st_size, reverse=True)
            if not nemo_files:
                raise FileNotFoundError(f"No .nemo file found in {model_dir}")
            map_loc = "cuda" if cuda else "cpu"
            self._model = nemo_asr.models.ASRModel.restore_from(
                str(nemo_files[0]), map_location=map_loc
            )

        elif backend == "sherpa_onnx":
            import sherpa_onnx
            # Use next(..., None) + explicit error to give clear messages on corrupt downloads
            encoder = next(model_dir.glob("encoder*.onnx"), None)
            decoder = next(model_dir.glob("decoder*.onnx"), None)
            joiner  = next(model_dir.glob("joiner*.onnx"), None)
            if not encoder or not decoder or not joiner:
                raise FileNotFoundError(
                    f"Missing ONNX files in {model_dir}. "
                    "Please delete and re-download this model."
                )
            tokens  = str(model_dir / "tokens.txt")
            self._model = sherpa_onnx.OfflineRecognizer.from_transducer(
                encoder=str(encoder),
                decoder=str(decoder),
                joiner=str(joiner),
                encoder=encoder,
                decoder=decoder,
                joiner=joiner,
                tokens=tokens,
                num_threads=4,
            )

        elif backend == "transformers":
            from transformers import pipeline
            device = 0 if cuda else -1
            self._model = pipeline(
                "automatic-speech-recognition",
                model=str(model_dir),
                device=device,
            )

        self._loaded_key = key

    def unload(self) -> None:
        with self._lock:
            if self._model is not None:
                del self._model
                self._model = None
                self._loaded_key = None
                try:
                    import torch
                    torch.cuda.empty_cache()
                except Exception:
                    pass


_model_cache = ParakeetModelCache()


# ── Download ──────────────────────────────────────────────────────────────────

def download_parakeet_model(
    key: str,
    on_progress: Callable[[str], None],
    on_done: Callable[[], None],
    on_error: Callable[[str], None],
) -> None:
    """Start a background daemon thread to download the model.
    on_done / on_error must be marshalled to the tkinter main thread
    by the caller using widget.after(0, callback)."""
    if key not in PARAKEET_MODELS:
        on_error(f"Unknown model key: {key}")
        return

    def _run():
        try:
            from huggingface_hub import snapshot_download
            on_progress(f"Downloading {PARAKEET_MODELS[key]['display']}…")
            local_dir = MODELS_DIR_PARAKEET / key
            local_dir.mkdir(parents=True, exist_ok=True)
            snapshot_download(
                repo_id=PARAKEET_MODELS[key]["hf_repo"],
                local_dir=str(local_dir),
            )
            on_done()
        except Exception as e:
            on_error(str(e))

    threading.Thread(target=_run, daemon=True).start()


def delete_parakeet_model(key: str) -> None:
    """Unload from cache (releases Windows file locks), then delete model dir."""
    import shutil
    _model_cache.unload()
    model_dir = MODELS_DIR_PARAKEET / key
    if model_dir.exists():
        shutil.rmtree(str(model_dir), ignore_errors=True)


# ── Inference ─────────────────────────────────────────────────────────────────

def transcribe_parakeet(
    audio_path: Path,
    model_key: str,
    backend: str,
    language: Optional[str],
    on_progress: Optional[Callable[[str], None]] = None,
) -> str:
    """Transcribe audio using the specified Parakeet model and backend."""
    if not model_key or model_key not in PARAKEET_MODELS:
        raise RuntimeError(
            "No Parakeet model selected. Please select a model in AI Models settings."
        )
    if not check_model_downloaded(model_key):
        raise RuntimeError(
            f"Parakeet model '{model_key}' not found on disk. "
            "Please re-download it from AI Models settings."
        )

    if on_progress:
        on_progress(f"Loading Parakeet model '{model_key}'…")

    model = _model_cache.get(model_key, backend)

    if on_progress:
        on_progress("Transcribing…")

    if backend == "nemo":
        result = model.transcribe([str(audio_path)])
        # NeMo 2.x returns Hypothesis objects (.text attr); older versions return plain strings
        r0 = result[0]
        return (r0.text if hasattr(r0, "text") else str(r0)).strip()

    elif backend == "sherpa_onnx":
        import numpy as np
        with wave.open(str(audio_path)) as wf:
            samples = (
                np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
                .astype(np.float32) / 32768.0
            )
        s = model.create_stream()
        s.accept_waveform(16000, samples)
        model.decode_streams([s])
        return s.result.text.strip()

    elif backend == "transformers":
        result = model(str(audio_path))
        return result["text"].strip()

    raise RuntimeError(f"Unknown backend: {backend}")
```

- [ ] **Step 2.4: Run tests**

```bash
python -m pytest tests/test_parakeet_transcription.py -v
```

Expected: all tests pass (backend-available tests return False since deps aren't installed — that's correct)

- [ ] **Step 2.5: Commit**

```bash
git add voiceink/services/parakeet_transcription.py tests/test_parakeet_transcription.py
git commit -m "feat: add parakeet_transcription service with model catalogue and backend detection"
```

---

## Task 3: Wire Parakeet into TranscriptionService and engine.py

**Files:**
- Modify: `voiceink/services/transcription.py:150-163` (transcribe dispatch)
- Modify: `voiceink/services/engine.py:203-205` (history model name)

- [ ] **Step 3.1: Write failing tests**

Append to `tests/test_parakeet_transcription.py`:

```python
def test_transcription_service_has_parakeet_provider():
    """TranscriptionService.transcribe() must handle provider='parakeet' without crashing
    when no model is selected (raises RuntimeError with helpful message)."""
    import tempfile, os
    from pathlib import Path
    from voiceink.models.settings import Settings
    from voiceink.services.transcription import TranscriptionService

    # Minimal temp settings file
    with tempfile.TemporaryDirectory() as tmp:
        settings = Settings.__new__(Settings)
        settings._data = {
            "transcription_provider": "parakeet",
            "parakeet_model_key": "",
            "parakeet_backend": "",
            "transcription_language": "auto",
        }
        settings._path = Path(tmp) / "settings.json"
        svc = TranscriptionService(settings)

        try:
            svc.transcribe(Path("dummy.wav"))
            assert False, "Should have raised RuntimeError"
        except RuntimeError as e:
            assert "parakeet" in str(e).lower() or "model" in str(e).lower()
        except Exception:
            pass  # Other errors acceptable — just must not KeyError silently
```

- [ ] **Step 3.2: Run to verify it fails**

```bash
python -m pytest tests/test_parakeet_transcription.py::test_transcription_service_has_parakeet_provider -v
```

Expected: `FAILED` — `transcription.py` doesn't handle `"parakeet"` yet

- [ ] **Step 3.3: Update `TranscriptionService.transcribe()` in `transcription.py`**

In the `transcribe()` method, add `parakeet` to the provider dispatch (around line 157):

```python
def transcribe(self, audio_path, on_progress=None):
    provider = self._settings.get_str("transcription_provider")

    if provider == "local":
        return self._transcribe_local(audio_path, on_progress)
    elif provider == "parakeet":
        return self._transcribe_parakeet(audio_path, on_progress)
    elif provider in ("groq", "openai", "deepgram", "custom"):
        return self._transcribe_cloud(audio_path, provider)
    else:
        return self._transcribe_local(audio_path, on_progress)
```

Add `_transcribe_parakeet()` method after `_transcribe_local()`:

```python
def _transcribe_parakeet(self, audio_path, on_progress=None):
    from voiceink.services.parakeet_transcription import transcribe_parakeet
    key     = self._settings.get_str("parakeet_model_key")
    backend = self._settings.get_str("parakeet_backend")
    lang    = self._settings.get_str("transcription_language") or None
    if lang == "auto":
        lang = None
    return transcribe_parakeet(audio_path, key, backend, lang, on_progress)
```

- [ ] **Step 3.4: Fix `engine.py` history model name recording**

In `voiceink/services/engine.py`, find lines 204–205 (the two-line `model_name = ...` assignment):

```python
# FIND AND DELETE THESE TWO LINES (the entire assignment):
model_name = self._settings.get_str("local_model_name") or \
             self._settings.get_str("transcription_provider")
```

Replace the entire two-line expression with:

```python
provider = self._settings.get_str("transcription_provider")
if provider == "local":
    model_name = self._settings.get_str("local_model_name") or "local"
elif provider == "parakeet":
    key     = self._settings.get_str("parakeet_model_key") or "unknown"
    backend = self._settings.get_str("parakeet_backend") or ""
    model_name = f"{key} ({backend})" if backend else key
else:
    model_name = provider
```

Note: this replaces those two lines entirely — do not keep the original assignment.

- [ ] **Step 3.5: Run all tests**

```bash
python -m pytest tests/test_parakeet_transcription.py -v
```

Expected: all tests pass

- [ ] **Step 3.6: Commit**

```bash
git add voiceink/services/transcription.py voiceink/services/engine.py
git commit -m "feat: wire parakeet provider into TranscriptionService and engine history"
```

---

## Task 4: Update `settings_window.py` — Badge and Provider Tab Guard

**Files:**
- Modify: `voiceink/ui/settings_window.py:662-673` (`_update_badge`)
- Modify: `voiceink/ui/settings_window.py:1098-1113` (Provider tab guard + trace)

- [ ] **Step 4.1: Update `_update_badge()` to handle `"parakeet"` provider**

In `settings_window.py`, find `_update_badge()` (around line 662). Add a `parakeet` branch before the `else`:

```python
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
```

- [ ] **Step 4.2: Fix Provider tab guard and trace**

In `settings_window.py` around line 1098, find and update two things:

**Part A — the guard block** (lines 1098–1100). Find:

```python
_saved_prov = self._settings.get_str("transcription_provider") or "groq"
if _saved_prov not in TRANSCRIPTION_PROVIDERS:
    _saved_prov = "groq"
prov_var = tk.StringVar(value=_saved_prov)
```

Replace with:

```python
_saved_prov = self._settings.get_str("transcription_provider") or "groq"
if _saved_prov not in TRANSCRIPTION_PROVIDERS and _saved_prov != "parakeet":
    _saved_prov = "groq"
# When saved provider is "parakeet", show "groq" in the cloud dropdown
# (Parakeet is a local model, not a cloud provider — intentional)
prov_var = tk.StringVar(value=_saved_prov if _saved_prov in TRANSCRIPTION_PROVIDERS else "groq")
```

**Part B — the trace** (around line 1111). Find and DELETE this line:

```python
prov_var.trace_add("write", lambda *_: self._settings.set(
    "transcription_provider", prov_var.get()))
```

Replace it with the guarded version (the `active_tab` variable already exists in scope from line ~680):

```python
def _on_cloud_prov_change(*_):
    # Only write when the user is actively on the Provider tab — prevents
    # overwriting a "parakeet" provider just by switching to this tab
    if active_tab[0] == "Provider":
        self._settings.set("transcription_provider", prov_var.get())

prov_var.trace_add("write", _on_cloud_prov_change)
```

Important: the old `lambda` trace must be removed — do not leave both traces in place.

- [ ] **Step 4.3: Smoke test by running the app**

```bash
cd d:/Development/voiceink-windows
python main.py
```

Open Settings → AI Models. Verify badge still shows correctly for the current provider. No errors in terminal.

- [ ] **Step 4.4: Commit**

```bash
git add voiceink/ui/settings_window.py
git commit -m "fix: update AI Models badge for parakeet provider; guard Provider tab from overwriting parakeet setting"
```

---

## Task 5: Build the NeMo Parakeet UI Section

**Files:**
- Modify: `voiceink/ui/settings_window.py` — `_build_ai_models_panel()` local tab section

This is the largest UI task. We add the NeMo section (dependency banner + 4 model cards) below the Whisper card stack, before the Language & Prompt section.

- [ ] **Step 5.1: Add helper function `_parakeet_dep_banner()`**

Add the following method to `SettingsWindow` (place after `_card()` helper, around line 289):

```python
def _dep_banner(self, parent, lines: list[str], btn_text: str,
                on_install: callable, warn_lines: list[str] = None):
    """Renders a dependency warning banner with an install button.
    Returns (banner_frame, install_btn, progress_lbl) for caller to control.
    Banner is initially packed; caller hides it on successful install."""
    BANNER_BG     = "#FFF8E1"   # warm amber tint
    BANNER_BORDER = "#F59E0B"
    WARN_FG       = "#92400E"

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
```

- [ ] **Step 5.2: Add helper `_parakeet_card()` for a single Parakeet model card**

Add the following method to `SettingsWindow` (after `_dep_banner`, around line 320):

```python
def _parakeet_card(self, parent, key: str, meta: dict,
                   is_selected: bool, is_downloaded: bool,
                   deps_ok: bool, on_action: callable, on_delete: callable):
    """Render one Parakeet model card. Returns (card_frame, action_btn, bg_widgets_list)."""
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

    # ── Title row with badges ──────────────────────────────────────────────
    title_row = tk.Frame(left, bg=bg)
    title_row.pack(fill="x")

    title_lbl = tk.Label(title_row, text=meta["display"], bg=bg, fg=HEADING,
                         font=FONT_BOLD)
    title_lbl.pack(side="left")

    # Backend badge
    BADGE_BG = ACCENT_LIGHT
    BADGE_FG = ACCENT
    tk.Frame(title_row, bg=bg, width=6).pack(side="left")
    tk.Label(title_row, text=meta["backend"].replace("_", "-"),
             bg=BADGE_BG, fg=BADGE_FG, font=FONT_SMALL,
             padx=5, pady=1).pack(side="left")

    # Quantization badge
    if meta.get("quantization"):
        tk.Frame(title_row, bg=bg, width=4).pack(side="left")
        tk.Label(title_row, text=meta["quantization"],
                 bg=BADGE_BG, fg=BADGE_FG, font=FONT_SMALL,
                 padx=5, pady=1).pack(side="left")

    # CUDA badge
    if meta.get("cuda_badge"):
        CUDA_BG = "#FEF3C7"
        CUDA_FG = "#D97706"
        label = "CUDA required" if meta["cuda_badge"] == "required" else "CUDA recommended"
        tk.Frame(title_row, bg=bg, width=4).pack(side="left")
        tk.Label(title_row, text=label,
                 bg=CUDA_BG, fg=CUDA_FG, font=FONT_SMALL,
                 padx=5, pady=1).pack(side="left")

    # ── Metadata line ──────────────────────────────────────────────────────
    size_str = (f"{meta['size_mb']} MB" if meta["size_mb"] < 1000
                else f"{meta['size_mb']/1000:.1f} GB")
    meta_parts = [meta["language"], size_str, meta["backend"].replace("_", "-")]
    if meta.get("quantization"):
        meta_parts.append(meta["quantization"])
    meta_lbl = tk.Label(left, text="  ·  ".join(meta_parts),
                        bg=bg, fg=TEXT_MUTED, font=FONT_SMALL, anchor="w")
    meta_lbl.pack(anchor="w", pady=(1, 0))

    # ── Description ────────────────────────────────────────────────────────
    desc_lbl = tk.Label(left, text=meta["description"], bg=bg, fg=TEXT_MUTED,
                        font=FONT_SMALL, justify="left", anchor="w", wraplength=500)
    desc_lbl.pack(anchor="w", pady=(2, 4))

    # ── Speed / Accuracy dots ──────────────────────────────────────────────
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

    # ── Action button ──────────────────────────────────────────────────────
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

    # Delete button (shown only when downloaded)
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
```

- [ ] **Step 5.3: Add the NeMo section builder method**

Add `_build_parakeet_nemo_section()` to `SettingsWindow`:

```python
def _build_parakeet_nemo_section(self, parent, cur_parakeet_key_var: list,
                                  parakeet_downloaded: set,
                                  parakeet_downloading: set,
                                  on_set_parakeet_default: callable,
                                  on_clear_parakeet: callable,
                                  refresh_all_parakeet: callable):
    """Build the NeMo backend section. Returns list of (key, card_frame, action_btn,
    del_btn, bg_widgets) tuples for use by refresh_all_parakeet_cards()."""
    import sys
    from voiceink.services.parakeet_transcription import (
        PARAKEET_MODELS, check_backend_available, check_cuda_available,
        check_model_downloaded, download_parakeet_model, delete_parakeet_model,
        BACKEND_PIP_CMDS,
    )

    IS_FROZEN = getattr(sys, 'frozen', False)
    nemo_keys = [k for k, m in PARAKEET_MODELS.items() if m["backend"] == "nemo"]
    nemo_ok   = [False]   # mutable container so inner functions can update it

    self._section_label(parent, "NVIDIA Parakeet — NeMo Backend")

    # ── Dependency banner ──────────────────────────────────────────────────
    banner_ref = [None]  # (wrap, install_btn, progress_lbl)

    def _check_and_maybe_hide_banner():
        nemo_ok[0] = check_backend_available("nemo")
        if nemo_ok[0] and banner_ref[0]:
            banner_ref[0][0].pack_forget()

    def _install_nemo():
        install_btn.configure(text="Installing…", state="disabled", bg=TEXT_MUTED)
        progress_lbl.configure(text="")

        def _run():
            import subprocess
            pkgs = BACKEND_PIP_CMDS["nemo"]
            proc = subprocess.Popen(
                [sys.executable, "-m", "pip", "install"] + pkgs,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                # Suppress console window flash on Windows
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
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
        # Show info-only banner, no install button
        info_wrap = tk.Frame(parent, bg=CONTENT_BG, padx=24)
        info_wrap.pack(fill="x", pady=(0, 4))
        info = tk.Frame(info_wrap, bg="#EFF6FF", highlightthickness=1,
                        highlightbackground="#BFDBFE")
        info.pack(fill="x")
        tk.Label(tk.Frame(info, bg="#EFF6FF", padx=14, pady=8),
                 text="ℹ  Parakeet NeMo models require running VoiceInk from source.\n"
                      "   pip install is not available in the packaged app.",
                 bg="#EFF6FF", fg="#1D4ED8", font=FONT_SMALL,
                 justify="left", anchor="w").pack(anchor="w")
        tk.Frame(info, bg="#EFF6FF", padx=14, pady=8).pack(fill="x")
        nemo_ok[0] = False
        install_btn = None
        progress_lbl = None
    else:
        nemo_ok[0] = check_backend_available("nemo")
        cuda_ok = check_cuda_available()
        cuda_text = ("✓  CUDA GPU detected — recommended for 0.6B+ models"
                     if cuda_ok else
                     "No CUDA GPU detected — only 110M model practical on CPU")
        cuda_fg = SUCCESS if cuda_ok else TEXT_MUTED

        if not nemo_ok[0]:
            lines     = ["⚠  NeMo backend not installed",
                         "   Requires: nemo_toolkit[asr] + torch"]
            warn_lines = ["   ⚠  NeMo is Linux-primary — may require WSL2 on Windows"]
            wrap, install_btn, progress_lbl = self._dep_banner(
                parent, lines, "Install NeMo + PyTorch", _install_nemo, warn_lines
            )
            # Append CUDA status line inside the banner inner frame
            banner_inner = wrap.winfo_children()[0].winfo_children()[0]
            tk.Label(banner_inner, text=f"   {cuda_text}",
                     bg="#FFF8E1", fg=cuda_fg, font=FONT_SMALL, anchor="w"
                     ).pack(anchor="w", before=banner_inner.winfo_children()[-2])
            banner_ref[0] = (wrap, install_btn, progress_lbl)
        else:
            install_btn = None
            progress_lbl = None

    # ── Model cards ────────────────────────────────────────────────────────
    stack = tk.Frame(parent, bg=CONTENT_BG, padx=24)
    stack.pack(fill="x", pady=(0, 8))

    card_registry = []  # list of (key, cf, action_btn, del_btn, bg_widgets)

    for key in nemo_keys:
        meta       = PARAKEET_MODELS[key]
        is_sel     = (cur_parakeet_key_var[0] == key)
        is_dl      = key in parakeet_downloaded
        deps_ok    = nemo_ok[0]

        def _make_action(k=key):
            def _action():
                if not nemo_ok[0]:
                    return
                if k in parakeet_downloading:
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

    def _start_download(k):
        parakeet_downloading.add(k)
        # Find and update the action_btn for this key
        for reg_key, cf, action_btn, del_btn, _ in card_registry:
            if reg_key == k:
                action_btn.configure(text="Downloading…", state="disabled",
                                     bg=TEXT_MUTED, activebackground=TEXT_MUTED)
                break

        def _on_progress(msg):
            pass  # static "Downloading…" state is sufficient

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
            on_progress=_on_progress,
            on_done=lambda: action_btn.after(0, _on_done),
            on_error=lambda e: action_btn.after(0, _on_error, e),
        )

    return card_registry, nemo_ok
```

- [ ] **Step 5.4: Smoke test NeMo section renders**

```bash
python main.py
```

Open Settings → AI Models → Local Model tab. Scroll down — NeMo section should appear below Whisper cards. If NeMo is not installed, banner shows. No errors in terminal.

- [ ] **Step 5.5: Commit**

```bash
git add voiceink/ui/settings_window.py
git commit -m "feat: add NeMo Parakeet UI section with dependency banner and model cards"
```

---

## Task 6: Build the Community UI Section (sherpa-onnx + HF Transformers)

**Files:**
- Modify: `voiceink/ui/settings_window.py`

- [ ] **Step 6.1: Add `_build_parakeet_community_section()` method**

Following the same pattern as `_build_parakeet_nemo_section()`, add:

```python
def _build_parakeet_community_section(self, parent, cur_parakeet_key_var: list,
                                       parakeet_downloaded: set,
                                       parakeet_downloading: set,
                                       on_set_parakeet_default: callable,
                                       on_clear_parakeet: callable,
                                       refresh_all_parakeet: callable):
    """Build the Community backend section (sherpa-onnx + HF Transformers).
    Returns list of (key, cf, action_btn, del_btn, bg_widgets) tuples."""
    import sys
    from voiceink.services.parakeet_transcription import (
        PARAKEET_MODELS, check_backend_available,
        check_model_downloaded, download_parakeet_model, delete_parakeet_model,
        BACKEND_PIP_CMDS,
    )

    IS_FROZEN = getattr(sys, 'frozen', False)
    onnx_keys = [k for k, m in PARAKEET_MODELS.items() if m["backend"] == "sherpa_onnx"]
    hf_keys   = [k for k, m in PARAKEET_MODELS.items() if m["backend"] == "transformers"]

    onnx_ok = [False]
    hf_ok   = [False]

    self._section_label(parent, "NVIDIA Parakeet — Community (sherpa-onnx · HF Transformers)")

    card_registry = []

    def _make_install_fn(backend_key, ok_ref, banner_ref_list):
        def _install():
            install_btn_ref = banner_ref_list[0][1]
            progress_lbl_ref = banner_ref_list[0][2]
            install_btn_ref.configure(text="Installing…", state="disabled", bg=TEXT_MUTED)
            progress_lbl_ref.configure(text="")

            def _run():
                import subprocess
                pkgs = BACKEND_PIP_CMDS[backend_key]
                proc = subprocess.Popen(
                    [sys.executable, "-m", "pip", "install"] + pkgs,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
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
        tk.Label(tk.Frame(info_inner, bg="#EFF6FF", padx=14, pady=8),
                 text="ℹ  Parakeet Community models require running VoiceInk from source.",
                 bg="#EFF6FF", fg="#1D4ED8", font=FONT_SMALL,
                 justify="left", anchor="w").pack(anchor="w")
    else:
        onnx_ok[0] = check_backend_available("sherpa_onnx")
        hf_ok[0]   = check_backend_available("transformers")

        # sherpa-onnx banner
        onnx_banner_ref = [None]
        if not onnx_ok[0]:
            wrap, btn, prog = self._dep_banner(
                parent,
                ["⚠  sherpa-onnx not installed",
                 "   Requires: sherpa-onnx (no PyTorch needed, CPU-first)"],
                "Install sherpa-onnx",
                _make_install_fn("sherpa_onnx", onnx_ok, onnx_banner_ref),
            )
            onnx_banner_ref[0] = (wrap, btn, prog)

        # HF Transformers banner
        hf_banner_ref = [None]
        if not hf_ok[0]:
            wrap, btn, prog = self._dep_banner(
                parent,
                ["⚠  transformers not installed (or version < 4.47)",
                 "   Requires: transformers>=4.47 + torch + torchaudio"],
                "Install HF Transformers",
                _make_install_fn("transformers", hf_ok, hf_banner_ref),
            )
            hf_banner_ref[0] = (wrap, btn, prog)

    # ── Model cards (sherpa-onnx) ──────────────────────────────────────────
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

    # ── Model cards (HF Transformers) ──────────────────────────────────────
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

    def _start_download(k, backend):
        parakeet_downloading.add(k)
        for reg_key, cf, action_btn, del_btn, _ in card_registry:
            if reg_key == k:
                action_btn.configure(text="Downloading…", state="disabled",
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

    return card_registry
```

- [ ] **Step 6.2: Smoke test community section renders**

```bash
python main.py
```

Scroll to bottom of Local Model tab. Both NeMo and Community sections visible. sherpa-onnx and HF banners shown if not installed.

- [ ] **Step 6.3: Commit**

```bash
git add voiceink/ui/settings_window.py
git commit -m "feat: add Community Parakeet UI section (sherpa-onnx + HF Transformers)"
```

---

## Task 7: Wire Sections into `_build_ai_models_panel()` with Shared State

**Files:**
- Modify: `voiceink/ui/settings_window.py` — `_build_ai_models_panel()` local tab section

- [ ] **Step 7.1: Add shared Parakeet state and section calls**

In `_build_ai_models_panel()`, after the Whisper `stack_wrap` for-loop ends (around line 1026 — after the last Whisper card is rendered), add before the Language & Prompt section:

```python
# ── Shared Parakeet state ──────────────────────────────────────────────────
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

parakeet_card_registries: list = []   # populated by section builders

def on_set_parakeet_default(key, backend):
    cur_parakeet_key_var[0] = key
    self._settings.set("parakeet_model_key", key)
    self._settings.set("parakeet_backend", backend)
    self._settings.set("transcription_provider", "parakeet")
    self._settings.set("local_model_name", "")
    # Clear Whisper default highlight
    cur_key_var[0] = None
    _refresh_all_cards()
    _update_badge()
    _refresh_all_parakeet_cards()

def on_clear_parakeet():
    cur_parakeet_key_var[0] = ""
    self._settings.set("parakeet_model_key", "")
    self._settings.set("parakeet_backend", "")
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
                continue   # leave "Downloading…" state untouched

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

# Patch the existing Whisper set_default() closure so that selecting a Whisper
# model also clears the Parakeet selection and refreshes Parakeet card states.
# Important: set_default() is defined earlier in the same _build_ai_models_panel
# scope (around line 831). We rebind it here in the same scope after Parakeet state
# is set up. The existing Whisper set_default call sites (action button commands)
# already hold a reference to the name 'set_default' from the enclosing scope,
# so rebinding the name here does NOT update those command= bindings.
# Therefore: instead of rebinding, directly append the Parakeet-clearing code
# into the existing set_default() function body by modifying it BEFORE the
# Whisper card loop renders (move this block above the Whisper card for-loop),
# OR add an on_whisper_default callback parameter.
#
# Simplest correct approach: define _on_whisper_default_extra() and call it from
# inside the existing set_default via a mutable list:
_parakeet_refresh_hook: list = [None]  # populated after Parakeet sections are built

# Patch set_default to call the hook if set:
_original_set_default = set_default
def set_default(key):  # noqa: F811  — intentional rebind
    _original_set_default(key)
    cur_parakeet_key_var[0] = ""
    self._settings.set("parakeet_model_key", "")
    self._settings.set("parakeet_backend", "")
    if _parakeet_refresh_hook[0]:
        _parakeet_refresh_hook[0]()

# Note: set_default is rebound HERE before the Whisper card for-loop renders.
# The cards' command= lambdas capture the name 'set_default' by closure from
# this scope, so they will call the new version. Place this block BEFORE the
# `for key, meta in LOCAL_MODELS.items():` loop.

# ── Build NeMo section ─────────────────────────────────────────────────────
nemo_registry, _ = self._build_parakeet_nemo_section(
    lm_inner, cur_parakeet_key_var, parakeet_downloaded, parakeet_downloading,
    on_set_parakeet_default, on_clear_parakeet, _refresh_all_parakeet_cards,
)
parakeet_card_registries.append(nemo_registry)

# ── Build Community section ────────────────────────────────────────────────
comm_registry = self._build_parakeet_community_section(
    lm_inner, cur_parakeet_key_var, parakeet_downloaded, parakeet_downloading,
    on_set_parakeet_default, on_clear_parakeet, _refresh_all_parakeet_cards,
)
parakeet_card_registries.append(comm_registry)

# Now that _refresh_all_parakeet_cards is defined, wire it into the hook
# so the already-rendered Whisper set_default() closure can call it
_parakeet_refresh_hook[0] = _refresh_all_parakeet_cards
```

- [ ] **Step 7.2: Full smoke test**

```bash
python main.py
```

- Open Settings → AI Models → Local Model tab
- Scroll through: Whisper cards → NeMo section → Community section → Language & Prompt
- If any Parakeet backend is installed: Download button should work on a small model
- Select a Parakeet model as default → badge at top should update to "Parakeet · <model>"
- Switch to a Whisper model → Parakeet cards should lose their "Default" highlight
- Open Provider tab → provider dropdown should NOT reset to groq if Parakeet was active

- [ ] **Step 7.3: Commit**

```bash
git add voiceink/ui/settings_window.py
git commit -m "feat: wire Parakeet sections into AI Models panel with shared state and cross-selection"
```

---

## Task 8: Update requirements.txt and Final Polish

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 8.1: Add Parakeet optional dep comments to requirements.txt**

Append to `requirements.txt`:

```
# ── Optional — NVIDIA Parakeet NeMo backend ───────────────────────────────
# Uncomment and install manually if you want NeMo Parakeet models:
# Note: nemo_toolkit is Linux-primary; Windows support is experimental.
#nemo_toolkit[asr]>=2.0    # NVIDIA NeMo ASR framework
#torch>=2.0.0              # Required by NeMo

# ── Optional — Parakeet Community: sherpa-onnx (no PyTorch, CPU-first) ────
#sherpa-onnx               # ONNX runtime for quantized Parakeet models

# ── Optional — Parakeet Community: HF Transformers CTC ───────────────────
#transformers>=4.47.0      # Required for ParakeetForCTC auto-class resolution
#torchaudio                # Required by HF Transformers ASR pipeline
```

- [ ] **Step 8.2: Final full test run**

```bash
python -m pytest tests/test_parakeet_transcription.py -v
```

Expected: all tests pass

- [ ] **Step 8.3: Final smoke test — end to end**

```bash
python main.py
```

- Verify Local Model tab scrolls correctly through all sections
- Verify no console errors on startup
- Verify settings save/load correctly with `parakeet_model_key` and `parakeet_backend`

- [ ] **Step 8.4: Final commit**

```bash
git add requirements.txt
git commit -m "docs: add optional Parakeet dependency comments to requirements.txt"
```

---

## Summary

| Task | What it delivers |
|------|-----------------|
| 1 | Settings defaults for parakeet keys |
| 2 | Full `parakeet_transcription.py` service — catalogue, detection, download, cache, inference |
| 3 | TranscriptionService dispatch + engine.py history fix |
| 4 | Badge update + Provider tab guard fix |
| 5 | NeMo UI section with dep banner + 4 model cards |
| 6 | Community UI section (4 sherpa-onnx + 2 HF Transformers cards) |
| 7 | Shared state wiring — cross-selection, refresh, set-default |
| 8 | requirements.txt docs + final polish |
