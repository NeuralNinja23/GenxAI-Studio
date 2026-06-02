"""
Phase 6A - Failure Memory Recording Layer

Passive observability system. Records failures via the repository layer.
Does NOT influence generation decisions (Phase 6B concern).
"""

import os
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from app.core.logging import log

from .memory_access_layer import MemoryAccessLayer


_DB_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), "sentinel_memory.db"))


class FailureType(str, Enum):
    AST_FAILURE = "AST_FAILURE"
    ORACLE_REJECTION = "ORACLE_REJECTION"
    REFLECTION_EXHAUSTION = "REFLECTION_EXHAUSTION"
    KERNEL_ROLLBACK = "KERNEL_ROLLBACK"
    BRANCH_PRUNED = "BRANCH_PRUNED"
    PROJECTION_FAILURE = "PROJECTION_FAILURE"
    COMPILATION_FAILURE = "COMPILATION_FAILURE"
    RUNTIME_FAILURE = "RUNTIME_FAILURE"


class Severity:
    INFO = 0.2
    WARNING = 0.4
    ERROR = 0.7
    CRITICAL = 1.0


class FailureRecorder:
    """
    Singleton. All recording points call FailureRecorder.record().
    Storage is delegated to MemoryAccessLayer.
    """

    _instance: Optional["FailureRecorder"] = None

    @classmethod
    def get_instance(cls) -> "FailureRecorder":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._db = MemoryAccessLayer(_DB_PATH)
        log("FAILURE_MEMORY", f"✅ FailureRecorder initialized → {self._db.db_path}")

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
        Fire-and-forget - never raises, never blocks the caller.
        """

        failure_id = str(uuid.uuid4())
        ts = datetime.now(timezone.utc).isoformat()

        try:
            ok = self._db.insert_memory_record(
                failure_id=failure_id,
                timestamp=ts,
                failure_type=failure_type.value,
                severity=severity,
                reason=reason,
                project_id=project_id,
                branch_id=branch_id,
                component=component,
                node_type=node_type,
                tb=tb,
                entropy=entropy,
                ui_nodes=ui_nodes,
                api_nodes=api_nodes,
            )
            if ok:
                log(
                    "FAILURE_MEMORY",
                    f"📝 [{failure_type.value}] sev={severity:.1f} "
                    f"proj={project_id[:24]} comp={component} → {reason[:80]}",
                )
            else:
                raise RuntimeError("FailureRecorder repository write failed")
        except Exception as e:
            log("FAILURE_MEMORY", f"⚠️ Failed to record failure: {e}")


def record_failure(
    failure_type: FailureType,
    severity: float,
    reason: str,
    **kwargs,
) -> None:
    """Thin wrapper. Import and call directly from any recording point."""
    FailureRecorder.get_instance().record(failure_type, severity, reason, **kwargs)
