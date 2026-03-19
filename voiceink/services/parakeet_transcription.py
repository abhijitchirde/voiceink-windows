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
            # _load() is intentionally called while holding the lock.
            # This is safe because transcribe_parakeet() is always called
            # from a background thread, never from the tkinter main thread.
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
    # Only unload if this specific model is cached (avoids evicting a different hot model)
    if _model_cache._loaded_key == key:
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
            sample_rate = wf.getframerate()
            samples = (
                np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
                .astype(np.float32) / 32768.0
            )
        s = model.create_stream()
        s.accept_waveform(sample_rate, samples)
        model.decode_streams([s])
        return s.result.text.strip()

    elif backend == "transformers":
        result = model(str(audio_path))
        return result["text"].strip()

    raise RuntimeError(f"Unknown backend: {backend}")
