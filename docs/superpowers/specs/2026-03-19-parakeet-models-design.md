# NVIDIA Parakeet Models — Design Spec
**Date:** 2026-03-19
**Status:** Approved for implementation

---

## Overview

Add a comprehensive NVIDIA Parakeet speech-to-text section to the Local Model tab of the AI Models settings panel. Users can browse, download, and select Parakeet models across two backends — NeMo (official NVIDIA) and Community (sherpa-onnx ONNX + HF Transformers CTC). Each section has dependency detection, install banners, and model cards that match the existing Whisper card design language exactly.

---

## Platform Notes

**NeMo on Windows:** `nemo_toolkit` is officially Linux-primary. On Windows it may install via pip but has known dependency issues (apex, megatron-core, symlink limitations). Every NeMo card and the NeMo dependency banner will show a visible warning: "NeMo is Linux-primary — may require WSL2 on Windows." Users proceed at their own discretion. The banner Install button still runs the pip command; we do not block the user.

**Frozen PyInstaller builds:** The pip-install-in-background approach only works in a dev/venv environment. For frozen exe builds, Parakeet cards will show a persistent info note: "Run VoiceInk from source to enable Parakeet models." Detection of frozen state uses `getattr(sys, 'frozen', False)`.

---

## Scope

### In scope
- Two new section headers below the Whisper cards: "NVIDIA Parakeet — NeMo" and "NVIDIA Parakeet — Community"
- Per-section dependency detection banners (shown only when backend not installed)
- One-click dependency install buttons per backend (run pip via `sys.executable -m pip install ...` in background thread, stdout/stderr captured for error display)
- 10 Parakeet model cards across both sections (110m sherpa-onnx entries removed — confirmed repos do not exist on HF)
- CUDA detection badge on NeMo 0.6B+ cards
- Full download / set-as-default / delete state machine per card (same as Whisper)
- New `parakeet` transcription provider in settings and `TranscriptionService`
- `ParakeetModelCache` singleton (mirrors existing `ModelCache` pattern)
- Model storage under `%APPDATA%/VoiceInk/models/parakeet/<key>/` using `local_dir=` to avoid Windows symlink cache issues
- Update `_update_badge()` and Provider tab guard in `settings_window.py`
- Update `engine.py` history model name recording for `parakeet` provider

### Out of scope
- Streaming/real-time Parakeet inference
- Speaker diarization or TTS
- Language-specific Parakeet models (Japanese, Vietnamese, Basque, Danish)
- Automatic CUDA driver installation
- WSL2 setup guidance

---

## Model Catalogue

### Section 1 — NeMo Backend
**Pip command:** `sys.executable -m pip install "nemo_toolkit[asr]" torch`
**Min versions:** nemo_toolkit>=2.0, torch>=2.0
**Inference:** `nemo.collections.asr.models.ASRModel.restore_from(local_nemo_path)`
**Windows caveat banner:** shown on all NeMo cards and banner

| Key | Display Name | HF Repo | Size | Language | Speed | Acc | CUDA badge |
|-----|-------------|---------|------|----------|-------|-----|-----------|
| `parakeet-nemo-110m` | Parakeet 110M | `nvidia/parakeet-tdt_ctc-110m` | 459 MB | English | 4/5 | 3/5 | None |
| `parakeet-nemo-0.6b-v2` | Parakeet TDT 0.6B v2 | `nvidia/parakeet-tdt-0.6b-v2` | 2.47 GB | English | 3/5 | 4/5 | Recommended |
| `parakeet-nemo-0.6b-v3` | Parakeet TDT 0.6B v3 | `nvidia/parakeet-tdt-0.6b-v3` | 2.51 GB | 25 langs | 3/5 | 4/5 | Recommended |
| `parakeet-nemo-1.1b` | Parakeet TDT 1.1B | `nvidia/parakeet-tdt-1.1b` | 4.28 GB | English | 2/5 | 5/5 | Required |

**Download:** `huggingface_hub.snapshot_download(repo_id, local_dir=MODELS_DIR/"parakeet"/key)` → glob `*.nemo` in that dir to get the model path for `restore_from()`.

**CUDA detection:** `torch.cuda.is_available()` wrapped in `try/except ImportError` → shown in the NeMo banner.

### Section 2 — Community Backend

#### Sub-section A: sherpa-onnx (ONNX, no PyTorch needed)
**Pip command:** `sys.executable -m pip install sherpa-onnx`
**Inference:** `sherpa_onnx.OfflineRecognizer.from_transducer()` — TDT models use three ONNX files + tokens
**File structure per model dir:** `encoder.int8.onnx` (or `encoder.onnx`), `decoder.int8.onnx`, `joiner.int8.onnx`, `tokens.txt`
**Exact API call (named kwargs required, num_threads required):**
```python
recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
    encoder=str(encoder_path),
    decoder=str(decoder_path),
    joiner=str(joiner_path),
    tokens=str(tokens_path),
    num_threads=4,
)
```

| Key | Display Name | HF Repo | Size | Quant | Language | Speed | Acc |
|-----|-------------|---------|------|-------|----------|-------|-----|
| `parakeet-onnx-0.6b-v2-int8` | Parakeet 0.6B v2 INT8 | `csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8` | ~661 MB | INT8 | English | 3/5 | 3/5 |
| `parakeet-onnx-0.6b-v2-fp16` | Parakeet 0.6B v2 FP16 | `csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-fp16` | ~1.2 GB | FP16 | English | 3/5 | 4/5 |
| `parakeet-onnx-0.6b-v3-int8` | Parakeet 0.6B v3 INT8 | `csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8` | ~661 MB | INT8 | 25 langs | 3/5 | 3/5 |
| `parakeet-onnx-0.6b-v3-fp16` | Parakeet 0.6B v3 FP16 | `csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-fp16` | ~1.2 GB | FP16 | 25 langs | 3/5 | 4/5 |

**Download:** `huggingface_hub.snapshot_download(repo_id, local_dir=MODELS_DIR/"parakeet"/key)` → verify dir contains `*.onnx` and `tokens.txt`.

**Download detection:** `(MODELS_DIR/"parakeet"/key/"tokens.txt").exists()` and at least one `.onnx` file in that dir.

#### Sub-section B: HF Transformers CTC (official NVIDIA repos)
**Pip command:** `sys.executable -m pip install "transformers>=4.47.0" torch torchaudio`
**Min version:** transformers>=4.47.0 (required for ParakeetForCTC auto-class resolution)
**Inference:** `pipeline("automatic-speech-recognition", model=local_dir, device=0 if cuda else -1)`

| Key | Display Name | HF Repo | Size | Language | Speed | Acc |
|-----|-------------|---------|------|----------|-------|-----|
| `parakeet-hf-ctc-0.6b` | Parakeet CTC 0.6B | `nvidia/parakeet-ctc-0.6b` | ~2.3 GB | English | 3/5 | 4/5 |
| `parakeet-hf-ctc-1.1b` | Parakeet CTC 1.1B | `nvidia/parakeet-ctc-1.1b` | ~4.3 GB | English | 2/5 | 5/5 |

**Download:** `huggingface_hub.snapshot_download(repo_id, local_dir=MODELS_DIR/"parakeet"/key)` → pass `local_dir` to `pipeline(model=str(local_dir))`.

**Download detection:** `(MODELS_DIR/"parakeet"/key/"config.json").exists()`.

---

## UI Design

### Section Labels
Two new calls to `_section_label()` placed after the Whisper card stack, before Language & Prompt:
- `NVIDIA PARAKEET — NEMO BACKEND`
- `NVIDIA PARAKEET — COMMUNITY (sherpa-onnx · HF Transformers)`

### Dependency Banner

A bordered frame shown at the top of each Parakeet sub-section when the backend is not importable (or when `sys.frozen` is True). Hidden on successful install.

**NeMo banner layout:**
```
┌─────────────────────────────────────────────────────────────────┐
│ ⚠  NeMo backend not installed                                   │
│    Requires: nemo_toolkit[asr] + torch                          │
│    ⚠  NeMo is Linux-primary — may have issues on Windows        │
│    CUDA GPU: [detected ✓  / not detected]                       │
│    [Install NeMo + PyTorch]   [progress/error text inline]      │
└─────────────────────────────────────────────────────────────────┘
```

**sherpa-onnx banner:**
```
┌─────────────────────────────────────────────────────────────────┐
│ ⚠  sherpa-onnx not installed                                    │
│    Requires: sherpa-onnx (no PyTorch needed, CPU-first)         │
│    [Install sherpa-onnx]   [progress/error text inline]         │
└─────────────────────────────────────────────────────────────────┘
```

**HF Transformers banner:**
```
┌─────────────────────────────────────────────────────────────────┐
│ ⚠  transformers not installed (or version < 4.47)               │
│    Requires: transformers>=4.47 + torch + torchaudio            │
│    [Install HF Transformers]   [progress/error text inline]     │
└─────────────────────────────────────────────────────────────────┘
```

**Banner install flow:**
1. User clicks install button
2. Button → "Installing…" (disabled, `TEXT_MUTED` bg); all model cards in this section remain in `needs_deps` state (buttons stay disabled)
3. Background thread runs: `subprocess.run([sys.executable, "-m", "pip", "install", ...], capture_output=True, text=True)`
4. Inline progress label polls last line of stdout via `btn.after(500, _poll)` loop while thread is alive
5. On `returncode == 0`: marshal back to main thread via `btn.after(0, _on_install_done)` → banner hides, `_refresh_all_parakeet_cards()` called → cards transition from `needs_deps` to `downloadable`
6. On `returncode != 0` or exception: marshal via `btn.after(0, _on_install_error)` → button → "Retry" (`ERROR` bg), last stderr line shown inline in `ERROR` color; cards remain `needs_deps`

**Dep install in-progress state:** While installing, the entire banner section shows a subtle animated label ("Installing dependencies…") and all model cards in that section keep `needs_deps` buttons. No other state changes occur mid-install.

**Frozen exe banner (replaces install banner entirely):**
```
┌─────────────────────────────────────────────────────────────────┐
│ ℹ  Parakeet models require running VoiceInk from source.        │
│    pip install is not available in the packaged app.            │
└─────────────────────────────────────────────────────────────────┘
```

### Model Cards

Identical layout to Whisper cards. Additions per card:

**Inline badges (after title, same row, small font, ACCENT_LIGHT bg, ACCENT fg):**
- Backend badge: `NeMo` / `sherpa-onnx` / `HF Transformers`
- Quantization badge (where applicable): `INT8` / `FP16` / `FP32`
- CUDA badge (NeMo 0.6B+ and 1.1B only): `CUDA recommended` (amber: bg `#FEF3C7`, fg `#D97706`) or `CUDA required` (1.1B)

**Metadata line (below title row, above description, `TEXT_MUTED` small font):**
`{Language}  ·  {Size}  ·  {Backend}`
e.g. `English  ·  661 MB  ·  sherpa-onnx · INT8`

**Description text:** 1–2 sentences per model (defined in `PARAKEET_MODELS` dict).

**Speed/Accuracy dots:** Same 5-dot system, same `ACCENT` / `CARD_BORDER` colors.

**Right-side button states (same state machine as Whisper):**

| State | Condition | Button text | Button style |
|-------|-----------|-------------|--------------|
| `needs_deps` | Backend not installed | `Needs deps` | disabled, `TEXT_MUTED` bg |
| `downloadable` | Backend installed, not on disk | `Download` | `ACCENT` bg |
| `downloading` | Download in progress | `Downloading…` | disabled, `TEXT_MUTED` bg |
| `retry` | Download failed | `Retry` | `ERROR` bg |
| `set_default` | Downloaded, not selected | `Set as Default` | `ACCENT` bg |
| `default` | Currently selected | `Default` | `SUCCESS` bg, disabled |

**"Needs deps" button behaviour:** Clicking "Needs deps" does nothing (it is `state="disabled"`). The dependency banner above the section is the action point for installing.

**Delete button:** Same trash icon (🗗), `ERROR` bg, shown only when `state == set_default` or `state == default` (i.e. model is on disk). Calls `unload()` on `ParakeetModelCache` before `shutil.rmtree` to release Windows file locks.

**State refresh:** A single `_refresh_all_parakeet_cards()` function (mirrors `_refresh_all_cards()` for Whisper) is called after: dep install success, download success, download failure, set-as-default, delete. It iterates all 10 cards and re-evaluates their state from scratch.

**Switching between two downloaded Parakeet models:** When user clicks "Set as Default" on card B while card A is `default`, `_refresh_all_parakeet_cards()` updates card A → `set_default`, card B → `default`.

**Switching from Parakeet back to Whisper:** When a Whisper card's `set_default` is clicked, the Whisper `set_default()` sets `transcription_provider = "local"` and `parakeet_model_key = ""`. `_refresh_all_parakeet_cards()` is then called to clear the `default` badge from any Parakeet card (all become `set_default` or `downloadable`).

---

## Settings Changes

### New keys in `_DEFAULTS` (settings.py)

```python
"parakeet_model_key": "",   # e.g. "parakeet-nemo-110m" — empty = none selected
"parakeet_backend":   "",   # "nemo" | "sherpa_onnx" | "transformers" — empty = none
```

These default to `""`. Existing users upgrading get these keys added silently on first load via the existing `_data.update(saved)` pattern in `Settings._load()`.

### Provider changes

When a Parakeet model is set as default:
- `transcription_provider` → `"parakeet"`
- `parakeet_model_key` → model key string
- `parakeet_backend` → backend string
- `local_model_name` → `""` (clears Whisper selection)

When a Whisper model is set as default:
- `transcription_provider` → `"local"`
- `parakeet_model_key` → `""`

### `_update_badge()` update

Add `"parakeet"` branch:
```python
elif prov == "parakeet":
    key = self._settings.get_str("parakeet_model_key")
    label = PARAKEET_MODELS[key]["display"] if key in PARAKEET_MODELS else "no model"
    badge_lbl.configure(text=f"Parakeet  ·  {label}")
```

### Provider tab guard update

The guard at line ~1099 that resets unrecognised providers to `"groq"` must exclude `"parakeet"`:

```python
if _saved_prov not in TRANSCRIPTION_PROVIDERS and _saved_prov != "parakeet":
    _saved_prov = "groq"
```

When `_saved_prov == "parakeet"`, the Provider tab shows groq as selected in the dropdown (Parakeet is a local model, not a cloud provider — this is correct and expected). The `prov_var.trace_add("write", ...)` that auto-saves the provider must also be guarded — it must NOT write when the current saved provider is `"parakeet"` and the user has not explicitly changed the dropdown:

```python
def _on_prov_var_change(*_):
    # Only overwrite transcription_provider if the user is actively on the Provider tab
    # and has touched the dropdown (not just because the tab opened)
    if active_tab[0] == "Provider":
        self._settings.set("transcription_provider", prov_var.get())
```

The `active_tab` variable tracks the currently shown sub-tab ("Local Model" or "Provider"). This prevents the Provider tab's dropdown trace from silently overwriting a `"parakeet"` provider just by the user switching to that tab.

---

## Backend Architecture

### New file: `voiceink/services/parakeet_transcription.py`

```python
PARAKEET_MODELS: dict  # all 10 model definitions with keys:
                       # display, hf_repo, size_mb, language, speed, accuracy,
                       # backend, quantization, description, cuda_badge

MODELS_DIR_PARAKEET = MODELS_DIR / "parakeet"

def check_backend_available(backend: str) -> bool:
    """Safe import-check. Returns False on any ImportError or version mismatch."""

def check_cuda_available() -> bool:
    """Returns torch.cuda.is_available(), or False if torch not installed."""

def check_model_downloaded(key: str) -> bool:
    """Check local disk for model files per backend type."""

def download_parakeet_model(
    key: str,
    on_progress: Callable[[str], None],   # fires with status string; NOT per-byte
    on_done: Callable[[], None],           # marshalled to main thread via btn.after(0, on_done)
    on_error: Callable[[str], None],       # marshalled to main thread via btn.after(0, on_error, msg)
) -> None:
    """Runs in a daemon background thread.
    Uses huggingface_hub.snapshot_download(repo_id, local_dir=...).
    Progress: on_progress is called once at start ("Downloading model...") and once
    on completion. snapshot_download has no per-chunk callback; for large models the
    UI shows a static "Downloading…" state with the button disabled. This matches the
    existing Whisper download UX.
    Success/failure detection: check subprocess returncode is NOT used here —
    snapshot_download raises an exception on failure. on_done / on_error are marshalled
    back to the main tkinter thread using btn.after(0, callback) pattern (same as
    existing download_and_set() in settings_window.py)."""

def delete_parakeet_model(key: str) -> None:
    """Unloads from cache first (REQUIRED on Windows to release file locks),
    then shutil.rmtree(MODELS_DIR_PARAKEET / key, ignore_errors=True)."""

class ParakeetModelCache:
    """Single loaded model at a time. Thread-safe. Mirrors ModelCache.
    unload() must: set self._model = None, self._loaded_key = None,
    and call del on the old model reference + torch.cuda.empty_cache() if torch
    is available. This is required on Windows before any file deletion to release
    memory-mapped file handles held by NeMo and HF Transformers backends."""
    def get(self, key: str, backend: str) -> Any: ...
    def unload(self) -> None: ...

def transcribe_parakeet(
    audio_path: Path,
    model_key: str,
    backend: str,
    language: Optional[str],
    on_progress: Optional[Callable[[str], None]],
) -> str:
    """Dispatches to NeMo / sherpa-onnx / HF Transformers inference."""
```

#### Backend inference details

**NeMo:**
```python
model_dir = MODELS_DIR_PARAKEET / key
# Sort descending by file size; take the largest .nemo file (the full model checkpoint)
nemo_files = sorted(model_dir.glob("*.nemo"), key=lambda p: p.stat().st_size, reverse=True)
if not nemo_files:
    raise FileNotFoundError(f"No .nemo file found in {model_dir}")
nemo_file = nemo_files[0]
model = nemo_asr.models.ASRModel.restore_from(str(nemo_file), map_location="cuda" if cuda else "cpu")
result = model.transcribe([str(audio_path)])
return result[0].text
```

**sherpa-onnx (TDT transducer):**
```python
model_dir = MODELS_DIR_PARAKEET / key
# INT8 variant uses *.int8.onnx filenames; FP16/FP32 use *.onnx
encoder = str(next(model_dir.glob("encoder*.onnx")))
decoder = str(next(model_dir.glob("decoder*.onnx")))
joiner  = str(next(model_dir.glob("joiner*.onnx")))
tokens  = str(model_dir / "tokens.txt")
recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
    encoder=encoder, decoder=decoder, joiner=joiner,
    tokens=tokens, num_threads=4,
)
with wave.open(str(audio_path)) as wf:
    samples = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
s = recognizer.create_stream()
s.accept_waveform(16000, samples)
recognizer.decode_streams([s])
return s.result.text
```

**HF Transformers:**
```python
from transformers import pipeline
device = 0 if check_cuda_available() else -1
model_dir = MODELS_DIR_PARAKEET / key
pipe = pipeline("automatic-speech-recognition", model=str(model_dir), device=device)
result = pipe(str(audio_path))
return result["text"]
```

### `TranscriptionService` changes

Add `_transcribe_parakeet()` wrapper method:
```python
def _transcribe_parakeet(self, audio_path, on_progress=None) -> str:
    from voiceink.services.parakeet_transcription import transcribe_parakeet
    key     = self._settings.get_str("parakeet_model_key")
    backend = self._settings.get_str("parakeet_backend")
    lang    = self._settings.get_str("transcription_language") or None
    if lang == "auto":
        lang = None
    return transcribe_parakeet(audio_path, key, backend, lang, on_progress)
```

Add `"parakeet"` branch in `transcribe()`:
```python
elif provider == "parakeet":
    return self._transcribe_parakeet(audio_path, on_progress)
```

### `engine.py` history recording update

Lines 204–205 of `engine.py` currently produce just `"parakeet"` as the model name when the provider is `parakeet`. Replace with:

```python
provider = self._settings.get_str("transcription_provider")
if provider == "local":
    model_name = self._settings.get_str("local_model_name") or "local"
elif provider == "parakeet":
    key     = self._settings.get_str("parakeet_model_key") or "unknown"
    backend = self._settings.get_str("parakeet_backend") or ""
    model_name = f"{key} ({backend})" if backend else key
    # e.g. "parakeet-nemo-1.1b (nemo)" or "parakeet-onnx-0.6b-v3-int8 (sherpa_onnx)"
else:
    model_name = provider
```

---

## Model Storage Layout

```
%APPDATA%/VoiceInk/models/
  parakeet/
    parakeet-nemo-110m/
      parakeet_tdt_ctc-110m.nemo        ← NeMo: glob *.nemo to find
    parakeet-nemo-0.6b-v2/
      parakeet_tdt-0.6b-v2.nemo
    parakeet-nemo-0.6b-v3/
      parakeet_tdt-0.6b-v3.nemo
    parakeet-nemo-1.1b/
      parakeet_tdt-1.1b.nemo
    parakeet-onnx-0.6b-v2-int8/
      encoder.int8.onnx
      decoder.int8.onnx
      joiner.int8.onnx
      tokens.txt
    parakeet-onnx-0.6b-v2-fp16/
      encoder.onnx
      decoder.onnx
      joiner.onnx
      tokens.txt
    parakeet-onnx-0.6b-v3-int8/   (same structure)
    parakeet-onnx-0.6b-v3-fp16/   (same structure)
    parakeet-hf-ctc-0.6b/
      config.json                      ← HF Transformers: check config.json
      model.safetensors (or shards)
      ...
    parakeet-hf-ctc-1.1b/
      config.json
      ...
```

---

## Error Handling

| Scenario | Behaviour |
|----------|-----------|
| Backend not installed | "Needs deps" button (disabled); banner shown |
| Dep install fails | "Retry" button; stderr tail shown in ERROR color |
| Download fails | "Retry" button on card; error message inline |
| Model missing at transcription time | `RuntimeError("Parakeet model not found. Please re-download from AI Models settings.")` |
| NeMo on CPU with 1.1B | Card description: "Requires CUDA GPU — will be extremely slow on CPU" |
| `torch` not installed during CUDA check | Returns `False`, no crash |
| App is frozen (PyInstaller) | All Parakeet sections show frozen banner; no install buttons shown |
| Windows + NeMo | Banner always shows "NeMo is Linux-primary" warning alongside install button |

---

## File Changes Summary

| File | Change |
|------|--------|
| `voiceink/services/parakeet_transcription.py` | **New** — full Parakeet backend module |
| `voiceink/services/transcription.py` | Add `parakeet` provider dispatch + `_transcribe_parakeet()` wrapper |
| `voiceink/models/settings.py` | Add `parakeet_model_key` and `parakeet_backend` to `_DEFAULTS` |
| `voiceink/ui/settings_window.py` | Add two Parakeet sub-sections to `_build_ai_models_panel`; update `_update_badge()`; update Provider tab guard |
| `voiceink/app.py` (or engine.py) | Update history model name recording for `parakeet` provider |
| `requirements.txt` | Add comments for optional Parakeet deps with exact pip commands |
