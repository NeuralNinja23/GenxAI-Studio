# app/sentinel/failure_memory/failure_recorder.py
"""
Phase 6A — Failure Memory Recording Layer

Passive observability system. Records failures to SQLite.
Does NOT influence generation decisions (Phase 6B concern).

Single write interface for all 5 recording points:
  1. AST Projector         — syntax/validation failures per file
  2. Behavioral Oracle     — orphan components, dead state stores
  3. Mutation Engine       — reflection budget exhausted
  4. Execution Kernel      — rollbacks and commit failures
  5. Sentinel Core            — cyclic branch pruning
"""

import os
import sqlite3
import traceback
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from app.core.logging import log

# ─────────────────────────────────────────────────────────────
_DB_PATH = os.path.join(os.path.dirname(__file__), "sentinel_memory.db")
_DB_PATH = os.path.normpath(_DB_PATH)


# ─────────────────────────────────────────────────────────────
# Canonical Failure Types
# ─────────────────────────────────────────────────────────────
class FailureType(str, Enum):
    AST_FAILURE          = "AST_FAILURE"           # File-level syntax / validation error
    ORACLE_REJECTION     = "ORACLE_REJECTION"       # Hard oracle blocked the commit
    REFLECTION_EXHAUSTION = "REFLECTION_EXHAUSTION" # LLM retry budget exhausted
    KERNEL_ROLLBACK      = "KERNEL_ROLLBACK"        # Execution kernel rolled back
    BRANCH_PRUNED        = "BRANCH_PRUNED"          # Branch discarded (cycle / invalid topo)
    PROJECTION_FAILURE   = "PROJECTION_FAILURE"     # Full projection cycle failed
    COMPILATION_FAILURE  = "COMPILATION_FAILURE"    # Python/JS compile-time error
    RUNTIME_FAILURE      = "RUNTIME_FAILURE"        # Sandbox/health-check failure


# ─────────────────────────────────────────────────────────────
# Severity constants (use these at call sites)
# ─────────────────────────────────────────────────────────────
class Severity:
    INFO     = 0.2   # Informational, non-blocking
    WARNING  = 0.4   # Soft warning, partial success
    ERROR    = 0.7   # Hard failure, recoverable
    CRITICAL = 1.0   # Total failure, rollback required


# ─────────────────────────────────────────────────────────────
# FailureRecorder — singleton write interface
# ─────────────────────────────────────────────────────────────
class FailureRecorder:
    """
    Singleton. All recording points call FailureRecorder.record().
    Thread-safe via per-call sqlite3.connect() (WAL mode).
    """

    _instance: Optional["FailureRecorder"] = None
    _db_path: str = _DB_PATH

    @classmethod
    def get_instance(cls) -> "FailureRecorder":
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
                    CREATE TABLE IF NOT EXISTS memories (
                        failure_id    TEXT PRIMARY KEY,
                        timestamp     TEXT NOT NULL,
                        project_id    TEXT,
                        branch_id     TEXT,
                        failure_type  TEXT NOT NULL,
                        severity      REAL NOT NULL,
                        component     TEXT,
                        node_type     TEXT,
                        reason        TEXT,
                        traceback     TEXT,
                        entropy       REAL,
                        ui_nodes      INTEGER,
                        api_nodes     INTEGER,
                        resolved      INTEGER DEFAULT 0
                    )
                """)
                conn.commit()
            log("FAILURE_MEMORY", f"✅ FailureRecorder initialized → {self._db_path}")
        except Exception as e:
            log("FAILURE_MEMORY", f"⚠️ FailureRecorder DB init failed: {e}")

    def record(
        self,
        failure_type: FailureType,
        severity: float,
        reason: str,
        *,
        project_id: str = "",
        branch_id: str = "",
        component: str = "",
        node_type: str = "",
        tb: str = "",
        entropy: float = 0.0,
        ui_nodes: int = 0,
        api_nodes: int = 0,
    ) -> None:
        """
        Write one failure record to the memories table.
        Fire-and-forget — never raises, never blocks the caller.
        """
        failure_id = str(uuid.uuid4())
        ts = datetime.now(timezone.utc).isoformat()

        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute(
                    """
                    INSERT OR IGNORE INTO memories
                        (failure_id, timestamp, project_id, branch_id,
                         failure_type, severity, component, node_type,
                         reason, traceback, entropy, ui_nodes, api_nodes, resolved)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,0)
                    """,
                    (
                        failure_id, ts, project_id, branch_id,
                        failure_type.value, severity, component, node_type,
                        reason, tb, entropy, ui_nodes, api_nodes,
                    ),
                )
                conn.commit()
            log(
                "FAILURE_MEMORY",
                f"📝 [{failure_type.value}] sev={severity:.1f} "
                f"proj={project_id[:24]} comp={component} → {reason[:80]}",
            )
        except Exception as e:
            log("FAILURE_MEMORY", f"⚠️ Failed to record failure: {e}")


# ─────────────────────────────────────────────────────────────
# Module-level convenience — avoids get_instance() at call sites
# ─────────────────────────────────────────────────────────────
def record_failure(
    failure_type: FailureType,
    severity: float,
    reason: str,
    **kwargs,
) -> None:
    """Thin wrapper. Import and call directly from any recording point."""
    FailureRecorder.get_instance().record(failure_type, severity, reason, **kwargs)
