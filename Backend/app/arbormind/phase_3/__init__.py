# phase_3/__init__.py

from .governor import CognitiveGovernor, GovernanceVerdict
from .attention import AttentionRouter, AttentionState
from .convergence import ConvergenceEngine, ConvergenceResult
from .mutation import MutationEngine, MutationRequest, MutationResult
from .validity import ValidityEvaluator, ValidityResult
from .circularity_monitor import CircularityMonitor
from .divergence_controller import DivergenceController, CognitiveBranch
from .mutation_law import (
    MutationLevel,
    MutationCategory,
    detect_stagnation,
    select_mutation_level,
    enforce_mutation_distance,
    FakeMutationError,
)
from .convergence_ledger import ConvergenceLedger, IterationSnapshot

__all__ = [
    "CognitiveGovernor",
    "GovernanceVerdict",
    "AttentionRouter",
    "AttentionState",
    "ConvergenceEngine",
    "ConvergenceResult",
    "MutationEngine",
    "MutationRequest",
    "MutationResult",
    "ValidityEvaluator",
    "ValidityResult",
    "CircularityMonitor",

    "DivergenceController",
    "CognitiveBranch",
    "MutationLevel",
    "MutationCategory",
    "detect_stagnation",
    "select_mutation_level",
    "enforce_mutation_distance",
    "FakeMutationError",
    "ConvergenceLedger",
    "IterationSnapshot",
]
