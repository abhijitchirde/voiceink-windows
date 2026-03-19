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
