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
                # Create standard S-0.8 Failure Memory Schema with stage tracking support
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
                        error_component TEXT
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
                    cursor.execute("ALTER TABLE failure_memory ADD COLUMN status TEXT DEFAULT 'candidate'")

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
        status: str = "candidate"
    ) -> bool:
        """Atomically inserts/updates verification failures to failure memory SQLite."""
        try:
            with sqlite3.connect(str(self.db_path), timeout=15.0) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO failure_memory (
                        failure_id, vector, error_class, cycle_id, details, 
                        verification_stage, error_field, error_file, error_component, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    status
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"[MEMORY_ACCESS_FAILURE] Write violation on failure memory insertion: {e}")
            return False

    def load_all_records(self) -> List[Tuple[str, np.ndarray, str, str, str, Optional[str], Optional[str], Optional[str], Optional[str]]]:
        """Loads and returns all failures stored in repulsion database."""
        try:
            with sqlite3.connect(str(self.db_path), timeout=10.0) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT failure_id, vector, error_class, cycle_id, details, 
                           verification_stage, error_field, error_file, error_component 
                    FROM failure_memory
                """)
                rows = cursor.fetchall()
                results = []
                for row in rows:
                    if len(row) == 9:
                        f_id, vec_str, err_class, cyc_id, details, stage, field, filename, comp = row
                    else:
                        f_id, vec_str, err_class, cyc_id, details = row[:5]
                        stage = field = filename = comp = None
                    vec = np.array(json.loads(vec_str), dtype=float)
                    results.append((f_id, vec, err_class, cyc_id, details, stage, field, filename, comp))
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

    def commit_memory(self, cycle_id: str) -> bool:
        """Promotes candidate memories to committed memories after a successful repair."""
        try:
            with sqlite3.connect(str(self.db_path), timeout=15.0) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE failure_memory 
                    SET status = 'committed'
                    WHERE cycle_id = ? AND status = 'candidate'
                """, (cycle_id,))
                conn.commit()
                return True
        except Exception as e:
            print(f"[MEMORY_ACCESS_FAILURE] Failed to commit memory for cycle {cycle_id}: {e}")
            return False
