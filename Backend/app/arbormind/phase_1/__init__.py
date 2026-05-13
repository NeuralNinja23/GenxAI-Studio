# phase_1/__init__.py

from .failure_memory import FailureMemory, FailureMemoryEntry
from .state import FailureSeverity, FailureRecord, ExecutionState, ExecutionStatus
from .state_gate import StateGate, ForbiddenStateError, DivergenceViolationError
from .canonical_fingerprint import (
    compute_fingerprint,
    CanonicalFingerprint,
    BehavioralTrace,
    SemanticTag,
    classify_semantic_tag,
)

__all__ = [
    "FailureMemory",
    "FailureMemoryEntry",
    "FailureSeverity",
    "FailureRecord",
    "ExecutionState",
    "ExecutionStatus",
    "StateGate",
    "ForbiddenStateError",
    "DivergenceViolationError",
    "compute_fingerprint",
    "CanonicalFingerprint",
    "BehavioralTrace",
    "SemanticTag",
    "classify_semantic_tag",
]
