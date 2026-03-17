"""
AI Enhancement service — Windows equivalent of AIEnhancementService.swift.
Calls OpenAI-compatible APIs (OpenAI, Groq, Gemini, Anthropic, Ollama, custom).
"""

import json
import time
from typing import Optional
import httpx


PROVIDER_CONFIG = {
    "openai":     {"url": "https://api.openai.com/v1/chat/completions",                                "default_model": "gpt-4o-mini",             "auth": "bearer"},
    "anthropic":  {"url": "https://api.anthropic.com/v1/messages",                                    "default_model": "claude-haiku-4-5-20251001","auth": "anthropic"},
    "groq":       {"url": "https://api.groq.com/openai/v1/chat/completions",                          "default_model": "llama-3.1-8b-instant",     "auth": "bearer"},
    "gemini":     {"url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", "default_model": "gemini-2.0-flash-001",     "auth": "bearer"},
    "cerebras":   {"url": "https://api.cerebras.ai/v1/chat/completions",                              "default_model": "llama3.1-8b",              "auth": "bearer"},
    "mistral":    {"url": "https://api.mistral.ai/v1/chat/completions",                               "default_model": "mistral-small-latest",     "auth": "bearer"},
    "openrouter": {"url": "https://openrouter.ai/api/v1/chat/completions",                            "default_model": "openai/gpt-4o-mini",       "auth": "bearer"},
    "ollama":     {"url": None,                                                                        "default_model": "mistral",                  "auth": "none"},
    "custom":     {"url": None,                                                                        "default_model": "",                         "auth": "bearer"},
}

AVAILABLE_MODELS = {
    "openai":     ["gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini"],
    "anthropic":  ["claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
    "groq":       ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "qwen/qwen3-32b"],
    "gemini":     ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash-001"],
    "cerebras":   ["llama3.1-8b", "qwen-3-235b-a22b-instruct-2507"],
    "mistral":    ["mistral-large-latest", "mistral-medium-latest", "mistral-small-latest"],
    "openrouter": [],
    "ollama":     [],
    "custom":     [],
}


class AIEnhancementService:
    def __init__(self, settings, prompt_store):
        self._settings = settings
        self._prompt_store = prompt_store
        self._last_request_time: Optional[float] = None
        self._rate_limit_interval = 1.0

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    @property
    def is_configured(self) -> bool:
        provider = self._settings.get_str("ai_provider")
        if provider == "ollama":
            return True  # no API key needed
        api_key = self._settings.get_str("ai_api_key")
        return bool(api_key.strip())

    @property
    def is_enabled(self) -> bool:
        return self._settings.get_bool("ai_enhancement_enabled") and self.is_configured

    def enhance(self, text: str) -> tuple[str, float]:
        """Returns (enhanced_text, duration_seconds)."""
        start = time.time()
        result = self._make_request_with_retry(text, max_retries=3)
        return result, time.time() - start

    def get_active_prompt(self):
        prompt_id = self._settings.get("selected_prompt_id")
        if prompt_id:
            p = self._prompt_store.get_by_id(prompt_id)
            if p:
                return p
        prompts = self._prompt_store.prompts
        return prompts[0] if prompts else None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_system_message(self) -> str:
        prompt = self.get_active_prompt()
        if prompt is None:
            return "Clean up this transcription. Fix grammar and punctuation."
        return prompt.final_prompt_text

    def _make_request(self, text: str) -> str:
        provider = self._settings.get_str("ai_provider")
        api_key = self._settings.get_str("ai_api_key")
        model = self._settings.get_str("ai_model")

        config = PROVIDER_CONFIG.get(provider, PROVIDER_CONFIG["openai"])
        if not model:
            model = config["default_model"]

        system_msg = self._build_system_message()
        user_msg = f"\n<TRANSCRIPT>\n{text}\n</TRANSCRIPT>"

        if provider == "ollama":
            return self._call_ollama(system_msg, user_msg, model)
        elif provider == "anthropic":
            return self._call_anthropic(api_key, model, system_msg, user_msg)
        else:
            url = config["url"]
            if provider == "custom":
                url = self._settings.get_str("custom_ai_base_url")
                model = self._settings.get_str("custom_ai_model") or model
            return self._call_openai_compat(url, api_key, model, system_msg, user_msg)

    def _make_request_with_retry(self, text: str, max_retries: int = 3) -> str:
        delay = 1.0
        last_error = None
        for attempt in range(max_retries):
            try:
                self._wait_for_rate_limit()
                result = self._make_request(text)
                self._last_request_time = time.time()
                return result
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429 or e.response.status_code >= 500:
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise
            except (httpx.NetworkError, httpx.TimeoutException) as e:
                last_error = e
                time.sleep(delay)
                delay *= 2
        raise RuntimeError(f"AI enhancement failed after {max_retries} retries: {last_error}")

    def _wait_for_rate_limit(self):
        if self._last_request_time is not None:
            elapsed = time.time() - self._last_request_time
            if elapsed < self._rate_limit_interval:
                time.sleep(self._rate_limit_interval - elapsed)

    # ------------------------------------------------------------------
    # Provider implementations
    # ------------------------------------------------------------------

    def _call_openai_compat(
        self, url: str, api_key: str, model: str, system_msg: str, user_msg: str
    ) -> str:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            "temperature": 0.3,
        }
        with httpx.Client(timeout=30) as client:
            resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    def _call_anthropic(
        self, api_key: str, model: str, system_msg: str, user_msg: str
    ) -> str:
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "max_tokens": 4096,
            "system": system_msg,
            "messages": [{"role": "user", "content": user_msg}],
        }
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
            )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"].strip()

    def _call_ollama(self, system_msg: str, user_msg: str, model: str) -> str:
        base_url = self._settings.get_str("ollama_base_url") or "http://localhost:11434"
        model = self._settings.get_str("ollama_model") or model or "mistral"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            "stream": False,
        }
        with httpx.Client(timeout=60) as client:
            resp = client.post(f"{base_url}/api/chat", json=payload)
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()
