"""
Audio recorder — Windows equivalent of CoreAudioRecorder.swift.
Uses sounddevice (WASAPI backend on Windows) to capture microphone audio
and writes a 16-bit 16kHz mono WAV file suitable for whisper.
"""

import threading
import time
import wave
from pathlib import Path
from typing import Callable, Optional
import numpy as np

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False


SAMPLE_RATE = 16000   # whisper expects 16 kHz
CHANNELS = 1
DTYPE = "int16"
BLOCK_SIZE = 1024     # ~64ms at 16 kHz


class AudioMeter:
    """Real-time audio level tracker."""

    def __init__(self):
        self.average_power: float = 0.0
        self.peak_power: float = 0.0
        self._lock = threading.Lock()
        self._smoothed_avg: float = 0.0
        self._smoothed_peak: float = 0.0

    def update(self, samples: np.ndarray):
        if len(samples) == 0:
            return
        rms = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))
        peak = float(np.max(np.abs(samples.astype(np.float32))))

        # Normalise to 0-1 (int16 range)
        norm_rms = min(rms / 32767.0, 1.0)
        norm_peak = min(peak / 32767.0, 1.0)

        with self._lock:
            self._smoothed_avg = self._smoothed_avg * 0.6 + norm_rms * 0.4
            self._smoothed_peak = self._smoothed_peak * 0.6 + norm_peak * 0.4
            self.average_power = self._smoothed_avg
            self.peak_power = self._smoothed_peak

    def reset(self):
        with self._lock:
            self._smoothed_avg = 0.0
            self._smoothed_peak = 0.0
            self.average_power = 0.0
            self.peak_power = 0.0


class AudioRecorder:
    """
    Records from a microphone to a WAV file.

    Usage:
        recorder = AudioRecorder()
        recorder.start(output_path)
        ...
        recorder.stop()   # writes file
    """

    def __init__(self):
        self._stream: Optional[object] = None
        self._frames: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._recording = False
        self._output_path: Optional[Path] = None
        self.meter = AudioMeter()
        self.on_level_update: Optional[Callable[[float, float], None]] = None
        self._level_timer: Optional[threading.Timer] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_devices(self) -> list[dict]:
        """Return list of available input devices."""
        if not SOUNDDEVICE_AVAILABLE:
            return []
        devices = []
        for i, d in enumerate(sd.query_devices()):
            if d["max_input_channels"] > 0:
                devices.append({
                    "index": i,
                    "name": d["name"],
                    "channels": d["max_input_channels"],
                    "default_sample_rate": d["default_samplerate"],
                })
        return devices

    def get_default_input_device(self) -> Optional[int]:
        if not SOUNDDEVICE_AVAILABLE:
            return None
        try:
            return sd.default.device[0]
        except Exception:
            return None

    def start(self, output_path: Path, device_index: Optional[int] = None) -> bool:
        """Start recording. Returns True on success."""
        if not SOUNDDEVICE_AVAILABLE:
            return False
        if self._recording:
            return False

        self._frames = []
        self._output_path = output_path
        self._recording = True
        self.meter.reset()

        try:
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype=DTYPE,
                blocksize=BLOCK_SIZE,
                device=device_index,
                callback=self._audio_callback,
            )
            self._stream.start()
            self._start_level_timer()
            return True
        except Exception as e:
            self._recording = False
            raise RuntimeError(f"Failed to start recording: {e}") from e

    def stop(self) -> Optional[Path]:
        """Stop recording and write WAV file. Returns the output path."""
        if not self._recording:
            return None

        self._recording = False
        self._stop_level_timer()

        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        self.meter.reset()

        if not self._frames or self._output_path is None:
            return None

        return self._write_wav()

    @property
    def is_recording(self) -> bool:
        return self._recording

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        if not self._recording:
            return
        chunk = indata.copy().flatten()
        with self._lock:
            self._frames.append(chunk)
        self.meter.update(chunk)

    def _write_wav(self) -> Optional[Path]:
        try:
            with self._lock:
                audio_data = np.concatenate(self._frames).astype(np.int16)
            self._output_path.parent.mkdir(parents=True, exist_ok=True)
            with wave.open(str(self._output_path), "wb") as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(2)        # int16 = 2 bytes
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(audio_data.tobytes())
            return self._output_path
        except Exception:
            return None

    def _start_level_timer(self):
        self._fire_level_update()

    def _fire_level_update(self):
        if not self._recording:
            return
        if self.on_level_update:
            self.on_level_update(self.meter.average_power, self.meter.peak_power)
        self._level_timer = threading.Timer(0.05, self._fire_level_update)
        self._level_timer.daemon = True
        self._level_timer.start()

    def _stop_level_timer(self):
        if self._level_timer:
            self._level_timer.cancel()
            self._level_timer = None
