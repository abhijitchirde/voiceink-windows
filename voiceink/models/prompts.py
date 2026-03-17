"""
AI enhancement prompts — mirrors CustomPrompt / PredefinedPrompts from the Mac version.
"""

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import os


SYSTEM_INSTRUCTIONS = """You are a transcription enhancer. Your job is to take raw speech transcripts and improve them.

Rules:
- Fix grammar, punctuation, and spelling errors
- Remove filler words and false starts
- Format the text clearly and naturally
- Preserve the speaker's meaning and intent exactly
- Do NOT add information that wasn't spoken
- Do NOT change the language
- Return ONLY the enhanced text — no explanations, no preamble"""


@dataclass
class Prompt:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    prompt_text: str = ""
    icon: str = "doc.text"
    description: str = ""
    is_predefined: bool = False
    use_system_instructions: bool = True
    trigger_words: list[str] = field(default_factory=list)

    @property
    def final_prompt_text(self) -> str:
        if self.use_system_instructions:
            return SYSTEM_INSTRUCTIONS + "\n\n" + self.prompt_text
        return self.prompt_text


# Predefined prompt IDs (stable across sessions)
DEFAULT_PROMPT_ID = "00000000-0000-0000-0000-000000000001"
ASSISTANT_PROMPT_ID = "00000000-0000-0000-0000-000000000002"


def _create_predefined_prompts() -> list[Prompt]:
    return [
        Prompt(
            id=DEFAULT_PROMPT_ID,
            title="Clean Transcription",
            prompt_text="Clean up this transcript. Fix grammar and punctuation. Remove filler words like 'um', 'uh', 'you know'. Keep the original meaning.",
            icon="sparkles",
            description="Cleans up raw transcription text",
            is_predefined=True,
            use_system_instructions=True,
        ),
        Prompt(
            id=ASSISTANT_PROMPT_ID,
            title="AI Assistant",
            prompt_text="You are a helpful AI assistant. The user has spoken a request or question to you. Respond helpfully and concisely.",
            icon="brain",
            description="Treats transcription as a prompt to an AI assistant",
            is_predefined=True,
            use_system_instructions=False,
        ),
        Prompt(
            id="00000000-0000-0000-0000-000000000003",
            title="Professional Email",
            prompt_text="Rewrite this transcript as a professional, concise email. Use formal language. Add a subject line at the top.",
            icon="envelope",
            description="Formats transcription as a professional email",
            is_predefined=True,
            use_system_instructions=True,
        ),
        Prompt(
            id="00000000-0000-0000-0000-000000000004",
            title="Bullet Points",
            prompt_text="Convert this transcript into clear, concise bullet points. Each bullet should capture one key idea.",
            icon="list.bullet",
            description="Converts transcription to bullet points",
            is_predefined=True,
            use_system_instructions=True,
        ),
    ]


def _prompts_path() -> Path:
    app_data = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    directory = app_data / "VoiceInk"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "prompts.json"


class PromptStore:
    def __init__(self):
        self._path = _prompts_path()
        self._prompts: list[Prompt] = []
        self._load()

    def _load(self):
        predefined = {p.id: p for p in _create_predefined_prompts()}

        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                loaded: list[Prompt] = []
                for d in saved:
                    p = Prompt(
                        id=d.get("id", str(uuid.uuid4())),
                        title=d.get("title", ""),
                        prompt_text=d.get("prompt_text", ""),
                        icon=d.get("icon", "doc.text"),
                        description=d.get("description", ""),
                        is_predefined=d.get("is_predefined", False),
                        use_system_instructions=d.get("use_system_instructions", True),
                        trigger_words=d.get("trigger_words", []),
                    )
                    if p.id in predefined:
                        # Keep predefined text up to date but preserve user trigger_words
                        fresh = predefined[p.id]
                        p.title = fresh.title
                        p.prompt_text = fresh.prompt_text
                        p.use_system_instructions = fresh.use_system_instructions
                    loaded.append(p)
                    predefined.pop(p.id, None)
                # Add any new predefined prompts not yet saved
                self._prompts = loaded + list(predefined.values())
                return
            except Exception:
                pass

        self._prompts = list(predefined.values())
        self.save()

    def save(self):
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump([
                    {
                        "id": p.id,
                        "title": p.title,
                        "prompt_text": p.prompt_text,
                        "icon": p.icon,
                        "description": p.description,
                        "is_predefined": p.is_predefined,
                        "use_system_instructions": p.use_system_instructions,
                        "trigger_words": p.trigger_words,
                    }
                    for p in self._prompts
                ], f, indent=2)
        except Exception:
            pass

    @property
    def prompts(self) -> list[Prompt]:
        return list(self._prompts)

    def get_by_id(self, prompt_id: str) -> Optional[Prompt]:
        return next((p for p in self._prompts if p.id == prompt_id), None)

    def add(self, prompt: Prompt):
        self._prompts.append(prompt)
        self.save()

    def update(self, prompt: Prompt):
        for i, p in enumerate(self._prompts):
            if p.id == prompt.id:
                self._prompts[i] = prompt
                break
        self.save()

    def delete(self, prompt_id: str):
        self._prompts = [p for p in self._prompts if p.id != prompt_id]
        self.save()


prompt_store = PromptStore()
