# app/sentinel/failure_memory/memory_access_layer.py
"""
MemoryAccessLayer (S-0.9)
Abstract data repository isolating database/storage engine access 
for repulsion metrics and failure registries, resolving absolute SQLite paths robustly.
"""

import os
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Tuple, Any, Optional
import numpy as np

class MemoryAccessLayer:
    """
    Unified decoupled data coordinator managing physical storage boundaries (SQLite, Mongo, etc.) 
    with dynamic path resolution.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = Path(db_path).resolve()
        else:
            # Absolute default path inside Backend app context
            backend_base = Path(__file__).parent.parent.parent.parent.resolve()
            self.db_path = backend_base / "app" / "sentinel" / "failure_memory" / "sentinel_memory.db"

        # Ensure directory structure exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        try:
            with sqlite3.connect(str(self.db_path), timeout=10.0) as conn:
                cursor = conn.cursor()
                # Create standard S-0.8 Failure Memory Schema with stage tracking support and enriched metadata
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS failure_memory (
                        failure_id TEXT PRIMARY KEY,
                        vector TEXT NOT NULL,
                        error_class TEXT,
                        cycle_id TEXT,
                        details TEXT,
                        verification_stage TEXT,
                        error_field TEXT,
                        error_file TEXT,
                        error_component TEXT,
                        status TEXT DEFAULT 'CANDIDATE',
                        failure_count INTEGER,
                        failure_type_histogram TEXT,
                        state_hash TEXT
                    )
                """)
                cursor.execute("PRAGMA table_info(failure_memory)")
                columns = {row[1] for row in cursor.fetchall()}
                if columns and "verification_stage" not in columns:
                    cursor.execute(
                        "ALTER TABLE failure_memory ADD COLUMN verification_stage TEXT"
                    )
                if columns and "error_field" not in columns:
                    cursor.execute("ALTER TABLE failure_memory ADD COLUMN error_field TEXT")
                if columns and "error_file" not in columns:
                    cursor.execute("ALTER TABLE failure_memory ADD COLUMN error_file TEXT")
                if columns and "error_component" not in columns:
                    cursor.execute("ALTER TABLE failure_memory ADD COLUMN error_component TEXT")
                if columns and "status" not in columns:
                    cursor.execute("ALTER TABLE failure_memory ADD COLUMN status TEXT DEFAULT 'CANDIDATE'")
                if columns and "failure_count" not in columns:
                    cursor.execute("ALTER TABLE failure_memory ADD COLUMN failure_count INTEGER")
                if columns and "failure_type_histogram" not in columns:
                    cursor.execute("ALTER TABLE failure_memory ADD COLUMN failure_type_histogram TEXT")
                if columns and "state_hash" not in columns:
                    cursor.execute("ALTER TABLE failure_memory ADD COLUMN state_hash TEXT")

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS memories (
                        failure_id TEXT PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        project_id TEXT,
                        branch_id TEXT,
                        failure_type TEXT NOT NULL,
                        severity REAL NOT NULL,
                        component TEXT,
                        node_type TEXT,
                        reason TEXT,
                        traceback TEXT,
                        entropy REAL,
                        ui_nodes INTEGER,
                        api_nodes INTEGER,
                        resolved INTEGER DEFAULT 0
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS repair_outcomes (
                        outcome_id TEXT PRIMARY KEY,
                        repair_goal_id TEXT NOT NULL,
                        success INTEGER NOT NULL,
                        delta_failures INTEGER NOT NULL,
                        branch_score REAL NOT NULL,
                        timestamp TEXT NOT NULL
                    )
                """)
                conn.commit()
        except sqlite3.OperationalError as e:
            # Gracefully handle locking / locked database state by creating memory db fallback if critical
            print(f"[MEMORY_ACCESS_FAILURE] Failed to initialize SQLite storage at {self.db_path}: {e}")

    def insert_failure_record(
        self,
        failure_id: str,
        vector: np.ndarray,
        error_class: str = "",
        cycle_id: str = "",
        details: str = "",
        verification_stage: Optional[str] = None,
        error_field: Optional[str] = None,
        error_file: Optional[str] = None,
        error_component: Optional[str] = None,
        status: str = "CANDIDATE",
        failure_count: Optional[int] = None,
        failure_type_histogram: Optional[str] = None,
        state_hash: Optional[str] = None
    ) -> bool:
        """Atomically inserts/updates verification failures to failure memory SQLite."""
        status = status.upper()
        print(f"[FAILURE_MEMORY] INSERT status={status} cycle={cycle_id}")
        try:
            with sqlite3.connect(str(self.db_path), timeout=15.0) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO failure_memory (
                        failure_id, vector, error_class, cycle_id, details, 
                        verification_stage, error_field, error_file, error_component, status,
                        failure_count, failure_type_histogram, state_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    failure_id,
                    json.dumps(vector.tolist()),
                    error_class,
                    cycle_id,
                    details,
                    verification_stage,
                    error_field,
                    error_file,
                    error_component,
                    status,
                    failure_count,
                    failure_type_histogram,
                    state_hash
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"[MEMORY_ACCESS_FAILURE] Write violation on failure memory insertion: {e}")
            return False

    def load_all_records(self) -> List[Tuple]:
        """Loads and returns all failures stored in repulsion database."""
        try:
            with sqlite3.connect(str(self.db_path), timeout=10.0) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT failure_id, vector, error_class, cycle_id, details, 
                           verification_stage, error_field, error_file, error_component,
                           status, failure_count, failure_type_histogram, state_hash
                    FROM failure_memory
                """)
                rows = cursor.fetchall()
                results = []
                for row in rows:
                    if len(row) == 13:
                        f_id, vec_str, err_class, cyc_id, details, stage, field, filename, comp, status, failure_count, hist, shash = row
                    elif len(row) == 9:
                        f_id, vec_str, err_class, cyc_id, details, stage, field, filename, comp = row
                        status = "candidate"
                        failure_count = None
                        hist = None
                        shash = None
                    else:
                        f_id, vec_str, err_class, cyc_id, details = row[:5]
                        stage = field = filename = comp = None
                        status = "candidate"
                        failure_count = None
                        hist = None
                        shash = None
                    vec = np.array(json.loads(vec_str), dtype=float)
                    results.append((f_id, vec, err_class, cyc_id, details, stage, field, filename, comp, status, failure_count, hist, shash))
                return results
        except Exception as e:
            print(f"[MEMORY_ACCESS_FAILURE] Read violation on failure memory lookup: {e}")
            return []

    def insert_memory_record(
        self,
        failure_id: str,
        timestamp: str,
        failure_type: str,
        severity: float,
        reason: str,
        project_id: str = "",
        branch_id: str = "",
        component: str = "",
        node_type: str = "",
        tb: str = "",
        entropy: float = 0.0,
        ui_nodes: int = 0,
        api_nodes: int = 0,
    ) -> bool:
        try:
            with sqlite3.connect(str(self.db_path), timeout=15.0) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO memories (
                        failure_id, timestamp, project_id, branch_id,
                        failure_type, severity, component, node_type,
                        reason, traceback, entropy, ui_nodes, api_nodes, resolved
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """, (
                    failure_id, timestamp, project_id, branch_id,
                    failure_type, severity, component, node_type,
                    reason, tb, entropy, ui_nodes, api_nodes,
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"[MEMORY_ACCESS_FAILURE] Write violation on memories insertion: {e}")
            return False

    def load_all_memory_records(self) -> List[Tuple[Any, ...]]:
        try:
            with sqlite3.connect(str(self.db_path), timeout=10.0) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT failure_id, timestamp, project_id, branch_id,
                           failure_type, severity, component, node_type,
                           reason, traceback, entropy, ui_nodes, api_nodes, resolved
                    FROM memories
                """)
                return cursor.fetchall()
        except Exception as e:
            print(f"[MEMORY_ACCESS_FAILURE] Read violation on memories lookup: {e}")
            return []

    def load_repulsion_records(self) -> List[Tuple]:
        """Loads and returns only COMMITTED failure records used by repulsion."""
        try:
            with sqlite3.connect(str(self.db_path), timeout=10.0) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT failure_id, vector, error_class, cycle_id, details, 
                           verification_stage, error_field, error_file, error_component,
                           status, failure_count, failure_type_histogram, state_hash
                    FROM failure_memory
                    WHERE status = 'COMMITTED'
                """)
                rows = cursor.fetchall()
                results = []
                for row in rows:
                    if len(row) == 13:
                        f_id, vec_str, err_class, cyc_id, details, stage, field, filename, comp, status, failure_count, hist, shash = row
                    elif len(row) == 9:
                        f_id, vec_str, err_class, cyc_id, details, stage, field, filename, comp = row
                        status = "COMMITTED"
                        failure_count = None
                        hist = None
                        shash = None
                    else:
                        f_id, vec_str, err_class, cyc_id, details = row[:5]
                        stage = field = filename = comp = None
                        status = "COMMITTED"
                        failure_count = None
                        hist = None
                        shash = None

                    # Phase 2 Invariant check
                    assert status == "COMMITTED", f"Contamination detected! Record {f_id} has status {status} but was loaded as repulsion record."

                    vec = np.array(json.loads(vec_str), dtype=float)
                    results.append((f_id, vec, err_class, cyc_id, details, stage, field, filename, comp, status, failure_count, hist, shash))
                return results
        except AssertionError as ae:
            print(f"[MEMORY_CONTAMINATION_INVARIANT_VIOLATION] {ae}")
            raise ae
        except Exception as e:
            print(f"[MEMORY_ACCESS_FAILURE] Read violation on committed failure memory lookup: {e}")
            return []

    def commit_memory(self, cycle_id: str) -> bool:
        """Promotes candidate memories to committed memories after a successful repair."""
        try:
            with sqlite3.connect(str(self.db_path), timeout=15.0) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE failure_memory 
                    SET status = 'COMMITTED'
                    WHERE cycle_id = ? AND status = 'CANDIDATE'
                """, (cycle_id,))
                rows_updated = cursor.rowcount
                conn.commit()
                # Change 4 Logging
                print(f"[FAILURE_MEMORY] TRANSITION CANDIDATE -> COMMITTED count={rows_updated} cycle={cycle_id}")
                return True
        except Exception as e:
            print(f"[MEMORY_ACCESS_FAILURE] Failed to commit memory for cycle {cycle_id}: {e}")
            return False

    def reject_memory(self, cycle_id: str, new_status: str = 'REJECTED_CYCLE') -> bool:
        """Transitions candidate memories to rejected/superseded memories."""
        new_status = new_status.upper()
        try:
            with sqlite3.connect(str(self.db_path), timeout=15.0) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE failure_memory 
                    SET status = ?
                    WHERE cycle_id = ? AND status = 'CANDIDATE'
                """, (new_status, cycle_id))
                rows_updated = cursor.rowcount
                conn.commit()
                # Change 4 Logging
                print(f"[FAILURE_MEMORY] TRANSITION CANDIDATE -> {new_status} cycle={cycle_id} count={rows_updated}")
                return True
        except Exception as e:
            print(f"[MEMORY_ACCESS_FAILURE] Failed to reject memory for cycle {cycle_id}: {e}")
            return False

    def insert_repair_outcome(
        self,
        goal_id: str,
        success: bool,
        delta_failures: int,
        branch_score: float
    ) -> bool:
        """Saves a repair outcome record to the database for historical learning."""
        import uuid
        import time
        try:
            with sqlite3.connect(str(self.db_path), timeout=15.0) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO repair_outcomes (
                        outcome_id, repair_goal_id, success, delta_failures, branch_score, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    f"outcome_{uuid.uuid4().hex[:6]}",
                    goal_id,
                    1 if success else 0,
                    delta_failures,
                    branch_score,
                    str(time.time())
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"[MEMORY_ACCESS_FAILURE] Failed to insert repair outcome for {goal_id}: {e}")
            return False

    def get_repair_goal_success_rate(self, goal_id: str) -> float:
        """Retrieves the success rate of a specific repair goal based on history."""
        try:
            with sqlite3.connect(str(self.db_path), timeout=10.0) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT success FROM repair_outcomes WHERE repair_goal_id = ?
                """, (goal_id,))
                rows = cursor.fetchall()
                if not rows:
                    return 1.0  # Optimistic default for unseen goals
                successes = sum(row[0] for row in rows)
                return float(successes / len(rows))
        except Exception as e:
            print(f"[MEMORY_ACCESS_FAILURE] Failed to fetch success rate for {goal_id}: {e}")
            return 1.0
