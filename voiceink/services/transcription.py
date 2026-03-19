"""
Transcription service — Windows equivalent of LocalTranscriptionService.swift
and the cloud transcription services.

Local: uses faster-whisper (CTranslate2 backend, runs on CPU or CUDA GPU).
Cloud: calls Groq / OpenAI / Deepgram / custom OpenAI-compatible endpoints.
"""

import os
import threading
import time
from pathlib import Path
from typing import Optional, Callable
import httpx

# faster-whisper is imported lazily so the app still starts if it's not installed yet
_whisper_module = None
_whisper_lock = threading.Lock()

MODELS_DIR = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "VoiceInk" / "models"

# Map short model names to their HuggingFace repo ids
_HF_REPO = {
    "tiny":     "Systran/faster-whisper-tiny",
    "base":     "Systran/faster-whisper-base",
    "small":    "Systran/faster-whisper-small",
    "medium":   "Systran/faster-whisper-medium",
    "large-v3": "Systran/faster-whisper-large-v3",
}


def _find_hf_cached_model(model_name: str) -> Optional[str]:
    """
    Directly walk the HuggingFace disk cache to find the model snapshot.
    Works inside a frozen PyInstaller exe without needing huggingface_hub at runtime.
    Cache layout: ~/.cache/huggingface/hub/models--Systran--faster-whisper-<name>/snapshots/<hash>/
    """
    repo_id = _HF_REPO.get(model_name, f"Systran/faster-whisper-{model_name}")
    # repo_id "Systran/faster-whisper-base" -> folder "models--Systran--faster-whisper-base"
    folder_name = "models--" + repo_id.replace("/", "--")

    # Possible cache roots
    # HF_HOME is the parent of the hub dir; HUGGINGFACE_HUB_CACHE points directly to the hub dir
    candidates = []
    hf_hub_cache = os.environ.get("HUGGINGFACE_HUB_CACHE")
    hf_home = os.environ.get("HF_HOME")
    if hf_hub_cache:
        candidates.append(Path(hf_hub_cache) / folder_name)
    elif hf_home:
        candidates.append(Path(hf_home) / "hub" / folder_name)
    candidates.append(Path.home() / ".cache" / "huggingface" / "hub" / folder_name)

    for cache_dir in candidates:
        snapshots = cache_dir / "snapshots"
        if not snapshots.exists():
            continue
        # Pick the first (usually only) snapshot hash directory that has model.bin
        for snap in snapshots.iterdir():
            if (snap / "model.bin").exists():
                return str(snap)
    return None

LOCAL_MODELS = {
    "tiny":      {"display": "Tiny (75 MB)",    "size_mb": 75,   "speed": 5.0, "accuracy": 0.6},
    "base":      {"display": "Base (145 MB)",   "size_mb": 145,  "speed": 4.0, "accuracy": 0.7},
    "small":     {"display": "Small (466 MB)",  "size_mb": 466,  "speed": 3.0, "accuracy": 0.8},
    "medium":    {"display": "Medium (1.5 GB)", "size_mb": 1500, "speed": 2.0, "accuracy": 0.9},
    "large-v3":  {"display": "Large v3 (3 GB)", "size_mb": 3000, "speed": 1.0, "accuracy": 1.0},
}


def _get_whisper():
    global _whisper_module
    with _whisper_lock:
        if _whisper_module is None:
            try:
                from faster_whisper import WhisperModel
                _whisper_module = WhisperModel
            except ImportError:
                raise RuntimeError(
                    "faster-whisper is not installed.\n"
                    "Run: pip install faster-whisper"
                )
    return _whisper_module


class ModelCache:
    """Keeps the last-used local Whisper model loaded in memory."""

    def __init__(self):
        self._model = None
        self._loaded_name: Optional[str] = None
        self._lock = threading.Lock()

    def get(self, model_name: str, device: str = "cpu", compute_type: str = "int8"):
        with self._lock:
            if self._model is not None and self._loaded_name == model_name:
                return self._model
            WhisperModel = _get_whisper()

            # Resolution order:
            # 1. APPDATA\VoiceInk\models\<name>  (manually placed)
            # 2. HuggingFace cache               (downloaded previously)
            # 3. Download from HuggingFace now   (short name triggers auto-download)
            local_path = MODELS_DIR / model_name
            if local_path.exists():
                model_id = str(local_path)
            else:
                hf_cache = _find_hf_cached_model(model_name)
                model_id = hf_cache if hf_cache else model_name

            # Try int8 first; fall back to float32 if unsupported on this CPU.
            last_err = None
            for ct in (compute_type, "float32"):
                try:
                    self._model = WhisperModel(model_id, device="cpu", compute_type=ct)
                    last_err = None
                    break
                except Exception as e:
                    last_err = e
            if last_err:
                raise last_err

            self._loaded_name = model_name
            return self._model

    def unload(self):
        with self._lock:
            self._model = None
            self._loaded_name = None


_model_cache = ModelCache()


class TranscriptionService:
    """
    Unified transcription service.

    provider: "local" | "groq" | "openai" | "deepgram" | "custom"
    """

    def __init__(self, settings):
        self._settings = settings

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def transcribe(
        self,
        audio_path: Path,
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> str:
        provider = self._settings.get_str("transcription_provider")

        if provider == "local":
            return self._transcribe_local(audio_path, on_progress)
        elif provider == "parakeet":
            return self._transcribe_parakeet(audio_path, on_progress)
        elif provider in ("groq", "openai", "deepgram", "custom"):
            return self._transcribe_cloud(audio_path, provider)
        else:
            return self._transcribe_local(audio_path, on_progress)

    def apply_word_replacements(self, text: str) -> str:
        replacements: dict = self._settings.get("word_replacements") or {}
        for src, dst in replacements.items():
            if src:
                text = text.replace(src, dst)
        return text

    def apply_filler_removal(self, text: str) -> str:
        if not self._settings.get_bool("filler_words_enabled"):
            return text
        filler_words: list = self._settings.get("filler_words") or []
        for word in filler_words:
            if not word:
                continue
            import re
            # Match whole word, case-insensitive, with optional surrounding spaces
            pattern = r"\b" + re.escape(word) + r"\b[,]?\s*"
            text = re.sub(pattern, " ", text, flags=re.IGNORECASE)
        return " ".join(text.split())  # collapse extra spaces

    # ------------------------------------------------------------------
    # Local transcription (faster-whisper)
    # ------------------------------------------------------------------

    def _transcribe_local(
        self,
        audio_path: Path,
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> str:
        model_name = self._settings.get_str("local_model_name") or "base"
        language = self._settings.get_str("transcription_language") or "auto"
        prompt = self._settings.get_str("transcription_prompt") or None

        if on_progress:
            on_progress(f"Loading model '{model_name}'...")

        model = _model_cache.get(model_name)

        if on_progress:
            on_progress("Transcribing...")

        lang_arg = None if language == "auto" else language

        segments, info = model.transcribe(
            str(audio_path),
            language=lang_arg,
            initial_prompt=prompt if prompt else None,
            beam_size=5,
            vad_filter=True,
        )

        text_parts = []
        for seg in segments:
            text_parts.append(seg.text.strip())

        return " ".join(text_parts).strip()

    # ------------------------------------------------------------------
    # Parakeet (NVIDIA NeMo / Sherpa-ONNX / Transformers) transcription
    # ------------------------------------------------------------------

    def _transcribe_parakeet(
        self,
        audio_path: Path,
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> str:
        from voiceink.services.parakeet_transcription import transcribe_parakeet
        key     = self._settings.get_str("parakeet_model_key")
        backend = self._settings.get_str("parakeet_backend")
        lang    = self._settings.get_str("transcription_language") or None
        if lang == "auto":
            lang = None
        return transcribe_parakeet(audio_path, key, backend, lang, on_progress)

    # ------------------------------------------------------------------
    # Cloud transcription
    # ------------------------------------------------------------------

    def _get_transcription_api_key(self, provider: str) -> str:
        """Return the API key for the given transcription provider."""
        key_map = {
            "groq":     "groq_transcription_api_key",
            "openai":   "openai_transcription_api_key",
            "deepgram": "deepgram_api_key",
            "custom":   "custom_transcription_api_key",
        }
        specific = self._settings.get_str(key_map.get(provider, "")) or ""
        # Fall back to legacy shared key if provider-specific key not set
        return specific or self._settings.get_str("transcription_api_key") or self._settings.get_str("ai_api_key") or ""

    def _transcribe_cloud(self, audio_path: Path, provider: str) -> str:
        api_key = self._get_transcription_api_key(provider)
        language = self._settings.get_str("transcription_language")
        lang_param = None if language == "auto" else language

        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        if provider == "groq":
            return self._transcribe_openai_compat(
                audio_bytes=audio_bytes,
                audio_filename=audio_path.name,
                base_url="https://api.groq.com/openai/v1/audio/transcriptions",
                api_key=api_key,
                model="whisper-large-v3",
                language=lang_param,
            )
        elif provider == "openai":
            return self._transcribe_openai_compat(
                audio_bytes=audio_bytes,
                audio_filename=audio_path.name,
                base_url="https://api.openai.com/v1/audio/transcriptions",
                api_key=api_key,
                model="whisper-1",
                language=lang_param,
            )
        elif provider == "deepgram":
            return self._transcribe_deepgram(audio_bytes, api_key, lang_param)
        elif provider == "custom":
            custom_url = self._settings.get_str("custom_transcription_base_url") or self._settings.get_str("custom_ai_base_url") or ""
            custom_model = self._settings.get_str("custom_transcription_model") or "whisper-1"
            return self._transcribe_openai_compat(
                audio_bytes=audio_bytes,
                audio_filename=audio_path.name,
                base_url=custom_url,
                api_key=api_key,
                model=custom_model,
                language=lang_param,
            )
        else:
            raise ValueError(f"Unknown cloud transcription provider: {provider}")

    def _transcribe_openai_compat(
        self,
        audio_bytes: bytes,
        audio_filename: str,
        base_url: str,
        api_key: str,
        model: str,
        language: Optional[str],
    ) -> str:
        files = {"file": (audio_filename, audio_bytes, "audio/wav")}
        data = {"model": model}
        if language:
            data["language"] = language

        headers = {"Authorization": f"Bearer {api_key}"}
        with httpx.Client(timeout=60) as client:
            resp = client.post(base_url, headers=headers, files=files, data=data)
        resp.raise_for_status()
        return resp.json().get("text", "").strip()

    def _transcribe_deepgram(
        self, audio_bytes: bytes, api_key: str, language: Optional[str]
    ) -> str:
        params = {"model": "nova-2", "smart_format": "true"}
        if language:
            params["language"] = language
        headers = {
            "Authorization": f"Token {api_key}",
            "Content-Type": "audio/wav",
        }
        with httpx.Client(timeout=60) as client:
            resp = client.post(
                "https://api.deepgram.com/v1/listen",
                headers=headers,
                params=params,
                content=audio_bytes,
            )
        resp.raise_for_status()
        results = resp.json()
        try:
            return results["results"]["channels"][0]["alternatives"][0]["transcript"].strip()
        except (KeyError, IndexError):
            return ""
