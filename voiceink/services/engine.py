"""
VoiceInk Engine — orchestrates recording → transcription → enhancement → paste.
Mirrors VoiceInkEngine.swift from the Mac version.

State machine:
  idle → recording → transcribing → (enhancing →) idle
"""

import threading
import tempfile
import time
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Optional

from voiceink.services.recorder import AudioRecorder
from voiceink.services.transcription import TranscriptionService
from voiceink.services.ai_enhancement import AIEnhancementService
from voiceink.services.clipboard import ClipboardPaster
from voiceink.models.transcription import TranscriptionRecord, store as transcription_store


class RecordingState(Enum):
    IDLE = auto()
    RECORDING = auto()
    TRANSCRIBING = auto()
    ENHANCING = auto()
    ERROR = auto()


class VoiceInkEngine:
    """
    Central engine.

    All state changes are announced via on_state_change(new_state).
    Transcription result is announced via on_transcription(raw, enhanced).
    Errors are announced via on_error(message).
    Audio level updates via on_level_update(avg, peak).
    """

    def __init__(self, settings, prompt_store):
        self._settings = settings
        self._recorder = AudioRecorder()
        self._transcription_service = TranscriptionService(settings)
        self._enhancement_service = AIEnhancementService(settings, prompt_store)
        self._paster = ClipboardPaster(settings)

        self._state = RecordingState.IDLE
        self._state_lock = threading.Lock()
        self._worker_thread: Optional[threading.Thread] = None

        self._recording_start_time: Optional[float] = None
        self._temp_audio_path: Optional[Path] = None
        self._last_raw_text: Optional[str] = None
        self._last_enhanced_text: Optional[str] = None

        # Callbacks (set by UI)
        self.on_state_change: Optional[Callable[[RecordingState], None]] = None
        self.on_transcription: Optional[Callable[[str, Optional[str]], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_level_update: Optional[Callable[[float, float], None]] = None
        self.on_progress: Optional[Callable[[str], None]] = None

        # Wire audio level callback
        self._recorder.on_level_update = self._handle_level_update

    # ------------------------------------------------------------------
    # Public API (called from hotkey manager or UI)
    # ------------------------------------------------------------------

    def toggle(self):
        """Toggle between recording and transcribing."""
        with self._state_lock:
            if self._state == RecordingState.IDLE:
                self._start_recording_locked()
            elif self._state == RecordingState.RECORDING:
                self._stop_recording_locked()
            # If busy (transcribing/enhancing) ignore the toggle

    def start_recording(self):
        with self._state_lock:
            if self._state == RecordingState.IDLE:
                self._start_recording_locked()

    def stop_recording(self):
        with self._state_lock:
            if self._state == RecordingState.RECORDING:
                self._stop_recording_locked()

    def cancel(self):
        """Cancel recording without transcribing."""
        with self._state_lock:
            if self._state == RecordingState.RECORDING:
                self._recorder.stop()
                self._set_state(RecordingState.IDLE)

    @property
    def state(self) -> RecordingState:
        return self._state

    @property
    def is_busy(self) -> bool:
        return self._state in (
            RecordingState.RECORDING,
            RecordingState.TRANSCRIBING,
            RecordingState.ENHANCING,
        )

    @property
    def last_raw_text(self) -> Optional[str]:
        return self._last_raw_text

    @property
    def last_enhanced_text(self) -> Optional[str]:
        return self._last_enhanced_text

    def paste_last(self):
        text = self._last_enhanced_text or self._last_raw_text
        if text:
            self._paster.paste_at_cursor(text)

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _start_recording_locked(self):
        device_index = self._settings.get("input_device_index")  # None = default
        self._temp_audio_path = Path(tempfile.mktemp(suffix=".wav", prefix="voiceink_"))
        try:
            self._recorder.start(self._temp_audio_path, device_index=device_index)
        except Exception as e:
            self._fire_error(f"Could not start recording: {e}")
            return
        self._recording_start_time = time.monotonic()
        self._set_state(RecordingState.RECORDING)

    def _stop_recording_locked(self):
        self._set_state(RecordingState.TRANSCRIBING)
        audio_path = self._recorder.stop()
        duration = (
            time.monotonic() - self._recording_start_time
            if self._recording_start_time is not None
            else 0.0
        )
        self._recording_start_time = None

        # Run transcription + enhancement in a background thread
        self._worker_thread = threading.Thread(
            target=self._process_audio,
            args=(audio_path, duration),
            daemon=True,
        )
        self._worker_thread.start()

    def _process_audio(self, audio_path: Optional[Path], duration: float):
        try:
            if audio_path is None or not audio_path.exists():
                self._fire_error("No audio was recorded.")
                self._set_state(RecordingState.IDLE)
                return

            # --- Transcription ---
            self._fire_progress("Transcribing...")
            t_start = time.monotonic()
            try:
                raw_text = self._transcription_service.transcribe(
                    audio_path, on_progress=self._fire_progress
                )
            except Exception as e:
                self._fire_error(f"Transcription failed: {e}")
                self._set_state(RecordingState.IDLE)
                return
            t_duration = time.monotonic() - t_start

            raw_text = self._transcription_service.apply_filler_removal(raw_text)
            raw_text = self._transcription_service.apply_word_replacements(raw_text)

            if not raw_text.strip():
                self._fire_progress("No speech detected.")
                self._set_state(RecordingState.IDLE)
                return

            # --- AI Enhancement (optional) ---
            enhanced_text: Optional[str] = None
            e_duration: Optional[float] = None
            prompt_name: Optional[str] = None
            ai_model: Optional[str] = None

            if self._enhancement_service.is_enabled:
                self._set_state(RecordingState.ENHANCING)
                self._fire_progress("Enhancing...")
                try:
                    active_prompt = self._enhancement_service.get_active_prompt()
                    prompt_name = active_prompt.title if active_prompt else None
                    enhanced_text, e_duration = self._enhancement_service.enhance(raw_text)
                    provider = self._settings.get_str("ai_provider")
                    model = self._settings.get_str("ai_model")
                    ai_model = f"{provider}/{model}" if model else provider
                except Exception as e:
                    # Enhancement failure is non-fatal — fall back to raw
                    self._fire_error(f"Enhancement failed (using raw): {e}")

            # --- Save to history ---
            provider = self._settings.get_str("transcription_provider")
            if provider == "local":
                model_name = self._settings.get_str("local_model_name") or "local"
            elif provider == "parakeet":
                key     = self._settings.get_str("parakeet_model_key") or "unknown"
                backend = self._settings.get_str("parakeet_backend") or ""
                model_name = f"{key} ({backend})" if backend else key
            else:
                model_name = provider
            record = TranscriptionRecord(
                text=raw_text,
                enhanced_text=enhanced_text,
                duration=duration,
                transcription_model=model_name,
                ai_model=ai_model,
                prompt_name=prompt_name,
                transcription_duration=t_duration,
                enhancement_duration=e_duration,
            )
            transcription_store.save(record)

            self._last_raw_text = raw_text
            self._last_enhanced_text = enhanced_text

            # --- Fire result callback ---
            if self.on_transcription:
                self.on_transcription(raw_text, enhanced_text)

            # --- Paste ---
            if self._settings.get_bool("auto_paste"):
                final_text = enhanced_text if enhanced_text else raw_text
                self._paster.paste_at_cursor(final_text)

        finally:
            # Clean up temp file
            if audio_path and audio_path.exists():
                try:
                    audio_path.unlink()
                except Exception:
                    pass
            self._set_state(RecordingState.IDLE)

    def _set_state(self, state: RecordingState):
        self._state = state
        if self.on_state_change:
            self.on_state_change(state)

    def _fire_error(self, message: str):
        if self.on_error:
            self.on_error(message)

    def _fire_progress(self, message: str):
        if self.on_progress:
            self.on_progress(message)

    def _handle_level_update(self, avg: float, peak: float):
        if self.on_level_update:
            self.on_level_update(avg, peak)
