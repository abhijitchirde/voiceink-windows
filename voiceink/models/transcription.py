"""
Transcription history model — mirrors the Mac Transcription SwiftData model.
Stored as a SQLite database via the built-in sqlite3 module (no ORM dependency).
"""

import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
import os


def _db_path() -> Path:
    app_data = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    directory = app_data / "VoiceInk"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "history.db"


@dataclass
class TranscriptionRecord:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    text: str = ""
    enhanced_text: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    duration: float = 0.0
    transcription_model: Optional[str] = None
    ai_model: Optional[str] = None
    prompt_name: Optional[str] = None
    transcription_duration: Optional[float] = None
    enhancement_duration: Optional[float] = None


class TranscriptionStore:
    """SQLite-backed transcription history store."""

    def __init__(self):
        self._db = _db_path()
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transcriptions (
                    id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    enhanced_text TEXT,
                    timestamp TEXT NOT NULL,
                    duration REAL NOT NULL DEFAULT 0,
                    transcription_model TEXT,
                    ai_model TEXT,
                    prompt_name TEXT,
                    transcription_duration REAL,
                    enhancement_duration REAL
                )
            """)
            conn.commit()

    def save(self, record: TranscriptionRecord):
        with self._conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO transcriptions
                  (id, text, enhanced_text, timestamp, duration,
                   transcription_model, ai_model, prompt_name,
                   transcription_duration, enhancement_duration)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.id,
                record.text,
                record.enhanced_text,
                record.timestamp.isoformat(),
                record.duration,
                record.transcription_model,
                record.ai_model,
                record.prompt_name,
                record.transcription_duration,
                record.enhancement_duration,
            ))
            conn.commit()

    def get_all(self, limit: int = 500) -> list[TranscriptionRecord]:
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT * FROM transcriptions
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,)).fetchall()
        return [self._row_to_record(r) for r in rows]

    def delete(self, record_id: str):
        with self._conn() as conn:
            conn.execute("DELETE FROM transcriptions WHERE id = ?", (record_id,))
            conn.commit()

    def delete_all(self):
        with self._conn() as conn:
            conn.execute("DELETE FROM transcriptions")
            conn.commit()

    def delete_older_than_days(self, days: int):
        cutoff = datetime.now().timestamp() - days * 86400
        with self._conn() as conn:
            conn.execute(
                "DELETE FROM transcriptions WHERE datetime(timestamp) < datetime(?)",
                (datetime.fromtimestamp(cutoff).isoformat(),)
            )
            conn.commit()

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> TranscriptionRecord:
        return TranscriptionRecord(
            id=row["id"],
            text=row["text"],
            enhanced_text=row["enhanced_text"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            duration=row["duration"] or 0.0,
            transcription_model=row["transcription_model"],
            ai_model=row["ai_model"],
            prompt_name=row["prompt_name"],
            transcription_duration=row["transcription_duration"],
            enhancement_duration=row["enhancement_duration"],
        )


# Module-level singleton
store = TranscriptionStore()
