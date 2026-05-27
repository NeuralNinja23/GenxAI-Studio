# app/failure_memory/failure_geometry.py
"""
V4 Failure Memory — Stage 6: Minimal Cognition
Implements the SQLite database schema and NumPy-based coordinate failure encoder.
"""

import os
import sqlite3
from typing import Any, Dict, List, Tuple, Optional
import numpy as np
from pathlib import Path

class FailureGeometry:
    """
    Manages SQLite-based vector storage for failure coordinates.
    Encodes structural and runtime failures into a 16-dimensional space.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Save db in the app/failure_memory directory
            base_dir = Path(__file__).parent
            self.db_path = str(base_dir / "failure_memory.db")
        else:
            self.db_path = db_path

        self._init_db()

    def _init_db(self):
        """Initialize the SQLite database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS failure_registry (
                id TEXT PRIMARY KEY,
                vector BLOB NOT NULL,
                error_class TEXT,
                cycle_id TEXT,
                details TEXT
            )
        """)
        conn.commit()
        conn.close()

    @staticmethod
    def encode_failure(
        node_count: int,
        edge_count: int,
        is_cyclic: bool,
        error_class: str,
        mutation_tier: int,
        error_len: int,
        api_node_count: int,
        ui_node_count: int,
        schema_node_count: int,
    ) -> np.ndarray:
        """
        Encode failure features deterministically into a 16-dimensional coordinate vector.
        """
        vector = np.zeros(16, dtype=np.float32)

        # 0. Node count (normalized)
        vector[0] = float(min(node_count / 100.0, 1.0))
        # 1. Edge count (normalized)
        vector[1] = float(min(edge_count / 100.0, 1.0))
        # 2. Cyclic topology flag
        vector[2] = 1.0 if is_cyclic else 0.0

        # 3. Error class weight
        error_weights = {
            "syntax": 0.1,
            "topology": 0.3,
            "behavioral": 0.5,
            "runtime": 0.7,
            "semantic": 0.9
        }
        vector[3] = error_weights.get(error_class.lower(), 0.0)

        # 4. Mutation tier
        vector[4] = float(mutation_tier / 5.0)
        # 5. Error message length indicator
        vector[5] = float(min(error_len / 500.0, 1.0))

        # 6. Node ratio UI/API
        denom = max(node_count, 1)
        vector[6] = float(api_node_count / denom)
        vector[7] = float(ui_node_count / denom)
        vector[8] = float(schema_node_count / denom)

        # 9. Average degree proxy
        vector[9] = float(min(edge_count / denom, 5.0) / 5.0)

        # 10-15. Deterministic hash padding for remainder
        for i in range(10, 16):
            # Deterministic noise based on inputs to pad remaining dimensions safely
            vector[i] = float(((node_count * i) + (edge_count * (16 - i))) % 10) / 10.0

        # Normalize the vector to unit length
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        return vector

    def insert_failure(self, failure_id: str, vector: np.ndarray, error_class: str, cycle_id: str, details: str) -> None:
        """Insert a compiled failure vector into the database registry."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        vector_bytes = vector.tobytes()
        cursor.execute(
            "INSERT OR REPLACE INTO failure_registry (id, vector, error_class, cycle_id, details) VALUES (?, ?, ?, ?, ?)",
            (failure_id, sqlite3.Binary(vector_bytes), error_class, cycle_id, details)
        )
        conn.commit()
        conn.close()

    def get_all_failures(self) -> List[Tuple[str, np.ndarray, str, str, str]]:
        """Retrieve all historical failures with their vectors parsed from buffer."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, vector, error_class, cycle_id, details FROM failure_registry")
        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            f_id, vec_bytes, err_class, cyc_id, details = row
            # Decode blob to float32 NumPy array
            vec = np.frombuffer(vec_bytes, dtype=np.float32)
            results.append((f_id, vec, err_class, cyc_id, details))
        return results

    def clear_registry(self) -> None:
        """Clear all stored failure logs."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM failure_registry")
        conn.commit()
        conn.close()
