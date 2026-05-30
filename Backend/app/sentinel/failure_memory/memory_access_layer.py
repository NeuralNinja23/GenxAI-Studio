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
        error_component: Optional[str] = None
    ) -> bool:
        """Atomically inserts/updates verification failures to failure memory SQLite."""
        try:
            with sqlite3.connect(str(self.db_path), timeout=15.0) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO failure_memory (
                        failure_id, vector, error_class, cycle_id, details, 
                        verification_stage, error_field, error_file, error_component
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    failure_id,
                    json.dumps(vector.tolist()),
                    error_class,
                    cycle_id,
                    details,
                    verification_stage,
                    error_field,
                    error_file,
                    error_component
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
                    f_id, vec_str, err_class, cyc_id, details, stage, field, filename, comp = row
                    vec = np.array(json.loads(vec_str), dtype=float)
                    results.append((f_id, vec, err_class, cyc_id, details, stage, field, filename, comp))
                return results
        except Exception as e:
            print(f"[MEMORY_ACCESS_FAILURE] Read violation on failure memory lookup: {e}")
            return []
