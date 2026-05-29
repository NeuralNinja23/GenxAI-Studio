# app/runtime/__init__.py
"""
V4 Runtime Package — Immutable Execution Substrate

Stage 1: Freeze Runtime

Exports the singleton execution kernel and key contracts.
All other runtime modules are import-protected —
cognitive modules must NOT import from this package directly.
"""

from .execution_kernel import ExecutionKernel, ProjectionCycleContext, get_kernel
from .execution_contracts import ExecutionContracts
from .leases import LeaseManager
from .drift_detection import DriftDetector, DriftReport, DriftSeverity, DriftResponse
from .transaction_engine import TransactionEngine
from .projection_snapshots import SnapshotManager

__all__ = [
    "ExecutionKernel",
    "ProjectionCycleContext",
    "get_kernel",
    "ExecutionContracts",
    "LeaseManager",
    "DriftDetector",
    "DriftReport",
    "DriftSeverity",
    "DriftResponse",
    "TransactionEngine",
    "SnapshotManager",
]
