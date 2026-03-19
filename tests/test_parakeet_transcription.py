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
