# app/sentinel/meaning_memory/meaning_recorder.py
"""
Phase 9 — Semantic Memory Recording Layer

Passive semantic observability system. Records user intents, experience patterns,
ontology structures, and workflow patterns to SQLite for future cognitive learning.
Does NOT influence generation decisions at this stage (purely Record Only).
"""

import os
import sqlite3
import uuid
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any

from app.core.logging import log

# ─────────────────────────────────────────────────────────────
_DB_PATH = os.path.join(os.path.dirname(__file__), "semantic_memory.db")
_DB_PATH = os.path.normpath(_DB_PATH)


class PatternType(str, Enum):
    INTENT = "intent"
    EXPERIENCE = "experience"
    ONTOLOGY = "ontology"
    WORKFLOW = "workflow"


class MeaningRecorder:
    """
    Singleton. All recording points call MeaningRecorder.record().
    Thread-safe via per-call sqlite3.connect() (WAL mode).
    """

    _instance: Optional["MeaningRecorder"] = None
    _db_path: str = _DB_PATH

    @classmethod
    def get_instance(cls) -> "MeaningRecorder":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._ensure_db()

    def _ensure_db(self):
        """Create DB and table if they don't exist."""
        try:
            os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS meanings (
                        meaning_id    TEXT PRIMARY KEY,
                        timestamp     TEXT NOT NULL,
                        project_id    TEXT,
                        prompt        TEXT,
                        pattern_type  TEXT NOT NULL,
                        payload       TEXT NOT NULL,
                        node_count    INTEGER,
                        edge_count    INTEGER
                    )
                """)
                conn.commit()
            log("SEMANTIC_MEMORY", f"✅ MeaningRecorder initialized → {self._db_path}")
        except Exception as e:
            log("SEMANTIC_MEMORY", f"⚠️ MeaningRecorder DB init failed: {e}")

    def record(
        self,
        pattern_type: PatternType,
        payload: Dict[str, Any],
        *,
        project_id: str = "",
        prompt: str = "",
        node_count: int = 0,
        edge_count: int = 0,
    ) -> None:
        """
        Write one semantic meaning record to the meanings table.
        Fire-and-forget — never raises, never blocks the caller.
        """
        meaning_id = str(uuid.uuid4())
        ts = datetime.now(timezone.utc).isoformat()
        payload_str = json.dumps(payload)

        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute(
                    """
                    INSERT OR IGNORE INTO meanings
                        (meaning_id, timestamp, project_id, prompt,
                         pattern_type, payload, node_count, edge_count)
                    VALUES (?,?,?,?,?,?,?,?)
                    """,
                    (
                        meaning_id, ts, project_id, prompt,
                        pattern_type.value, payload_str, node_count, edge_count,
                    ),
                )
                conn.commit()
            log(
                "SEMANTIC_MEMORY",
                f"📝 Saved semantic pattern [{pattern_type.value}] for project {project_id} with {node_count} nodes.",
            )
        except Exception as e:
            log("SEMANTIC_MEMORY", f"⚠️ Failed to record semantic meaning: {e}")


def record_meaning(
    pattern_type: PatternType,
    payload: Dict[str, Any],
    **kwargs,
) -> None:
    """Thin wrapper. Import and call directly from any recording point."""
    MeaningRecorder.get_instance().record(pattern_type, payload, **kwargs)
