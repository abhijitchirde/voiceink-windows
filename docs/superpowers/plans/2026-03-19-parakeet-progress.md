# Parakeet Implementation Progress

> Resume point for when token credits reset. Pick up from the first unchecked task.
>
> **Plan file:** `docs/superpowers/plans/2026-03-19-parakeet-models.md`
> **Spec file:** `docs/superpowers/specs/2026-03-19-parakeet-models-design.md`
> **Branch:** `development`

## Task Status

- [x] **Task 1** — Add `parakeet_model_key` and `parakeet_backend` to Settings defaults
  - Files: `voiceink/models/settings.py`, `tests/test_parakeet_transcription.py`
  - Commit: `43a48d9`
  - Status: ✅ Done + spec & quality reviewed

- [x] **Task 2** — Create `voiceink/services/parakeet_transcription.py`
  - Full model catalogue (10 models), backend detection, cache, download, inference
  - Commits: `0d7fc38` (initial), `2dfb842` (fixes: WAV sample rate, conditional cache evict)
  - Status: ✅ Done + spec & quality reviewed

- [x] **Task 3** — Wire parakeet into TranscriptionService and fix engine.py history
  - Files: `voiceink/services/transcription.py`, `voiceink/services/engine.py`
  - Status: ✅ Done + spec & quality reviewed

- [ ] **Task 4** — Update `settings_window.py` badge and Provider tab guard
  - Files: `voiceink/ui/settings_window.py`
  - What to do:
    1. In `_update_badge()`: add `parakeet` branch before `else` (see plan lines 720–737)
    2. Provider tab guard: change `if _saved_prov not in TRANSCRIPTION_PROVIDERS:` → add `and _saved_prov != "parakeet"` (plan lines 754–761)
    3. Remove old `prov_var.trace_add` lambda, replace with `_on_cloud_prov_change()` guard (plan lines 773–779)
    4. Smoke test: `python main.py` → open Settings → AI Models
    5. Commit

- [ ] **Task 5** — Build NeMo Parakeet UI section (`_dep_banner`, `_parakeet_card`, `_build_parakeet_nemo_section`)
  - Files: `voiceink/ui/settings_window.py`
  - See plan lines 809–1193 for full code

- [ ] **Task 6** — Build Community UI section (`_build_parakeet_community_section`)
  - Files: `voiceink/ui/settings_window.py`
  - See plan lines 1197–1446 for full code

- [ ] **Task 7** — Wire sections into `_build_ai_models_panel` with shared state
  - Files: `voiceink/ui/settings_window.py`
  - See plan lines 1451–1613 for full code
  - Key: set_default patching, `_parakeet_refresh_hook`, `_refresh_all_parakeet_cards`

- [ ] **Task 8** — Update `requirements.txt` and final polish
  - Append commented optional dep blocks (see plan lines 1622–1639)
  - Final test run + smoke test

## How to Resume

1. Check out branch: `git checkout development`
2. Verify tests pass: `python -m pytest tests/test_parakeet_transcription.py -v` (should be 13 passed)
3. Start from first unchecked task above using subagent-driven development
4. Follow the plan file for exact code — it has complete implementations for each step

## Notes

- The plan's sherpa-onnx OfflineRecognizer.from_transducer duplicate-kwargs bug has been fixed in Task 2 — the service file is correct
- settings_window.py is large — read it carefully before editing (especially around line 662 for badge, and ~1098 for provider guard)
- Tasks 5/6/7 all modify settings_window.py — do them sequentially, not in parallel
