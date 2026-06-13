# app/sentinel/experience/memory_access_layer.py
"""
MemoryAccessLayer for Sentinel Experience Repository & Transition Ledger (S-0.10).
Manages SQLite storage at app/sentinel/experience/sentinel_experience.db in an append-only, immutable manner.
"""

import os
import sqlite3
import json
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

class ExperienceMemoryAccessLayer:
    """
    Handles initialization, indexing, and append-only database operations for the Transition Ledger.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = Path(db_path).resolve()
        else:
            backend_base = Path(__file__).parent.parent.parent.parent.resolve()
            self.db_path = backend_base / "app" / "sentinel" / "experience" / "sentinel_experience.db"

        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Creates the tables and indexes if they do not exist."""
        try:
            with sqlite3.connect(str(self.db_path), timeout=10.0) as conn:
                cursor = conn.cursor()
                
                # Enable foreign key support (though we keep child keys loosely coupled for future revisions)
                cursor.execute("PRAGMA foreign_keys = ON;")

                # 1. state_transitions
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS state_transitions (
                        transition_id TEXT PRIMARY KEY,
                        parent_transition_id TEXT,
                        cycle_id TEXT,
                        workspace_id TEXT,
                        attempt_number INTEGER,
                        workspace_hash TEXT,
                        timestamp TEXT,
                        before_oracle REAL,
                        after_oracle REAL,
                        created_at TEXT
                    )
                """)

                # 2. transition_states
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS transition_states (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        transition_id TEXT,
                        before_failures TEXT,
                        after_failures TEXT,
                        before_verification_summary TEXT,
                        after_verification_summary TEXT,
                        created_at TEXT
                    )
                """)

                # 3. transition_intents
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS transition_intents (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        transition_id TEXT,
                        target_file TEXT,
                        scope TEXT,
                        repair_mode TEXT,
                        instruction TEXT,
                        prompt TEXT,
                        context_metadata TEXT,
                        created_at TEXT
                    )
                """)

                # 4. transition_artifacts
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS transition_artifacts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        transition_id TEXT,
                        before_source TEXT,
                        after_source TEXT,
                        diff TEXT,
                        compiler_output TEXT,
                        bundler_output TEXT,
                        runtime_output TEXT,
                        render_output TEXT,
                        created_at TEXT
                    )
                """)

                # Create indexes for fast structural experience retrieval
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_cycle_id ON state_transitions(cycle_id);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_workspace_id ON state_transitions(workspace_id);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_parent_transition_id ON state_transitions(parent_transition_id);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_attempt_number ON state_transitions(attempt_number);")
                
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_states_transition_id ON transition_states(transition_id);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_intents_transition_id ON transition_intents(transition_id);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_transition_id ON transition_artifacts(transition_id);")

                conn.commit()
        except sqlite3.OperationalError as e:
            print(f"[EXPERIENCE_DB_FAILURE] Failed to initialize SQLite storage at {self.db_path}: {e}")

    def insert_transition(
        self,
        transition_id: str,
        parent_transition_id: Optional[str],
        cycle_id: str,
        workspace_id: str,
        attempt_number: int,
        workspace_hash: str,
        before_oracle: float,
        after_oracle: float,
        # States
        before_failures: List[Dict[str, Any]],
        after_failures: List[Dict[str, Any]],
        before_verification_summary: Dict[str, Any],
        after_verification_summary: Dict[str, Any],
        # Intents
        target_file: Optional[str],
        scope: Optional[str],
        repair_mode: Optional[str],
        instruction: Optional[str],
        prompt: Optional[str],
        context_metadata: Dict[str, Any],
        # Artifacts
        before_source: Optional[str],
        after_source: Optional[str],
        diff: Optional[str],
        compiler_output: Optional[str],
        bundler_output: Optional[str],
        runtime_output: Optional[str],
        render_output: Optional[str]
    ) -> bool:
        """
        Atomically appends a complete observed transition to the ledger.
        This operation is raw, immutable, and append-only. No updates are allowed.
        """
        now = datetime.datetime.utcnow().isoformat()
        
        try:
            with sqlite3.connect(str(self.db_path), timeout=15.0) as conn:
                cursor = conn.cursor()
                
                # 1. Insert state_transitions
                cursor.execute("""
                    INSERT INTO state_transitions (
                        transition_id, parent_transition_id, cycle_id, workspace_id,
                        attempt_number, workspace_hash, timestamp, before_oracle, after_oracle, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    transition_id,
                    parent_transition_id,
                    cycle_id,
                    workspace_id,
                    attempt_number,
                    workspace_hash,
                    now,
                    before_oracle,
                    after_oracle,
                    now
                ))

                # 2. Insert transition_states
                cursor.execute("""
                    INSERT INTO transition_states (
                        transition_id, before_failures, after_failures,
                        before_verification_summary, after_verification_summary, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    transition_id,
                    json.dumps(before_failures),
                    json.dumps(after_failures),
                    json.dumps(before_verification_summary),
                    json.dumps(after_verification_summary),
                    now
                ))

                # 3. Insert transition_intents
                cursor.execute("""
                    INSERT INTO transition_intents (
                        transition_id, target_file, scope, repair_mode, instruction, prompt, context_metadata, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    transition_id,
                    target_file,
                    scope,
                    repair_mode,
                    instruction,
                    prompt,
                    json.dumps(context_metadata),
                    now
                ))

                # 4. Insert transition_artifacts
                cursor.execute("""
                    INSERT INTO transition_artifacts (
                        transition_id, before_source, after_source, diff,
                        compiler_output, bundler_output, runtime_output, render_output, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    transition_id,
                    before_source,
                    after_source,
                    diff,
                    compiler_output,
                    bundler_output,
                    runtime_output,
                    render_output,
                    now
                ))

                conn.commit()
                print(f"[EXPERIENCE_REPOSITORY] Logged transition_id={transition_id} cycle_id={cycle_id} attempt={attempt_number}")
                return True
        except Exception as e:
            print(f"[EXPERIENCE_DB_FAILURE] Write violation on transition insertion: {e}")
            return False

    def get_transition(self, transition_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a single transition object with all its states, intents, and artifacts.
        """
        try:
            with sqlite3.connect(str(self.db_path), timeout=10.0) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Fetch state_transitions
                t_row = cursor.execute("""
                    SELECT * FROM state_transitions WHERE transition_id = ?
                """, (transition_id,)).fetchone()
                
                if not t_row:
                    return None

                # Fetch states
                s_row = cursor.execute("""
                    SELECT * FROM transition_states WHERE transition_id = ?
                """, (transition_id,)).fetchone()

                # Fetch intents
                i_row = cursor.execute("""
                    SELECT * FROM transition_intents WHERE transition_id = ?
                """, (transition_id,)).fetchone()

                # Fetch artifacts
                a_row = cursor.execute("""
                    SELECT * FROM transition_artifacts WHERE transition_id = ?
                """, (transition_id,)).fetchone()

                return {
                    "transition_id": t_row["transition_id"],
                    "parent_transition_id": t_row["parent_transition_id"],
                    "cycle_id": t_row["cycle_id"],
                    "workspace_id": t_row["workspace_id"],
                    "attempt_number": t_row["attempt_number"],
                    "workspace_hash": t_row["workspace_hash"],
                    "timestamp": t_row["timestamp"],
                    "before_oracle": t_row["before_oracle"],
                    "after_oracle": t_row["after_oracle"],
                    "created_at": t_row["created_at"],
                    "states": {
                        "before_failures": json.loads(s_row["before_failures"]) if s_row else [],
                        "after_failures": json.loads(s_row["after_failures"]) if s_row else [],
                        "before_verification_summary": json.loads(s_row["before_verification_summary"]) if s_row else {},
                        "after_verification_summary": json.loads(s_row["after_verification_summary"]) if s_row else {}
                    } if s_row else None,
                    "intent": {
                        "target_file": i_row["target_file"] if i_row else None,
                        "scope": i_row["scope"] if i_row else None,
                        "repair_mode": i_row["repair_mode"] if i_row else None,
                        "instruction": i_row["instruction"] if i_row else None,
                        "prompt": i_row["prompt"] if i_row else None,
                        "context_metadata": json.loads(i_row["context_metadata"]) if i_row else {}
                    } if i_row else None,
                    "artifacts": {
                        "before_source": a_row["before_source"] if a_row else None,
                        "after_source": a_row["after_source"] if a_row else None,
                        "diff": a_row["diff"] if a_row else None,
                        "compiler_output": a_row["compiler_output"] if a_row else None,
                        "bundler_output": a_row["bundler_output"] if a_row else None,
                        "runtime_output": a_row["runtime_output"] if a_row else None,
                        "render_output": a_row["render_output"] if a_row else None
                    } if a_row else None
                }
        except Exception as e:
            print(f"[EXPERIENCE_DB_FAILURE] Read violation on transition lookup: {e}")
            return None

    def get_cycle_transitions(self, cycle_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all transitions registered under a specific cycle_id, sorted chronologically by attempt_number.
        """
        try:
            with sqlite3.connect(str(self.db_path), timeout=10.0) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT transition_id FROM state_transitions
                    WHERE cycle_id = ?
                    ORDER BY attempt_number ASC
                """, (cycle_id,))
                t_ids = [row[0] for row in cursor.fetchall()]
                
                results = []
                for t_id in t_ids:
                    t_details = self.get_transition(t_id)
                    if t_details:
                        results.append(t_details)
                return results
        except Exception as e:
            print(f"[EXPERIENCE_DB_FAILURE] Read violation on cycle transitions lookup: {e}")
            return []
