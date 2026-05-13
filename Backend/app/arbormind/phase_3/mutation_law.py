# mutation_law.py
#
# STEP 3: Strict mutation definitions and enforcement.
#
# Mutation is NOT:
#   - Regenerating code
#   - Tweaking variables
#   - Retrying with a different prompt
#
# Mutation IS a topology change.
# This module defines what that means in enforceable terms.

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Dict, Any, List, Optional
import time


# ═══════════════════════════════════════════════════════════════
# MUTATION LEVELS (strict hierarchy)
# ═══════════════════════════════════════════════════════════════

class MutationLevel(IntEnum):
    """
    Strictly ordered mutation severity.

    Level 0: NOT a mutation (gradient step / local fix)
    Level 1: NOT a mutation (gradient step / local fix)
    Level 2: Structural mutation (topology change)
    Level 3: Architectural mutation (paradigm change)

    Only Level 2+ is TRUE mutation.
    """
    GRADIENT = 0        # NOT mutation: small code edits, bug fixes
    LOCAL_FIX = 1       # NOT mutation: variable tweaks, prompt changes
    STRUCTURAL = 2      # TRUE mutation: API redesign, data model change, module split
    ARCHITECTURAL = 3   # TRUE mutation: monolith→micro, REST→event, sync→async


class MutationCategory(str, Enum):
    """Concrete mutation operations at each level."""

    # Level 0/1: Gradient steps (NOT mutations)
    CODE_FIX = "code_fix"
    VARIABLE_TWEAK = "variable_tweak"
    PROMPT_CHANGE = "prompt_change"
    IMPORT_FIX = "import_fix"

    # Level 2: Structural mutations
    API_REDESIGN = "api_redesign"
    DATA_MODEL_CHANGE = "data_model_change"
    MODULE_SPLIT = "module_split"
    MODULE_MERGE = "module_merge"
    STATE_MANAGEMENT_CHANGE = "state_management_change"
    ROUTING_CHANGE = "routing_change"
    SCHEMA_MIGRATION = "schema_migration"

    # Level 3: Architectural mutations
    MONOLITH_TO_MICROSERVICE = "monolith_to_microservice"
    REST_TO_EVENT_DRIVEN = "rest_to_event_driven"
    SYNC_TO_ASYNC = "sync_to_async"
    SQL_TO_NOSQL = "sql_to_nosql"
    FRAMEWORK_SWAP = "framework_swap"
    RENDERING_PARADIGM_CHANGE = "rendering_paradigm_change"


# Category → Level mapping (explicit, no inference)
_CATEGORY_LEVELS: Dict[MutationCategory, MutationLevel] = {
    # NOT mutations
    MutationCategory.CODE_FIX: MutationLevel.GRADIENT,
    MutationCategory.VARIABLE_TWEAK: MutationLevel.GRADIENT,
    MutationCategory.PROMPT_CHANGE: MutationLevel.LOCAL_FIX,
    MutationCategory.IMPORT_FIX: MutationLevel.LOCAL_FIX,

    # Level 2
    MutationCategory.API_REDESIGN: MutationLevel.STRUCTURAL,
    MutationCategory.DATA_MODEL_CHANGE: MutationLevel.STRUCTURAL,
    MutationCategory.MODULE_SPLIT: MutationLevel.STRUCTURAL,
    MutationCategory.MODULE_MERGE: MutationLevel.STRUCTURAL,
    MutationCategory.STATE_MANAGEMENT_CHANGE: MutationLevel.STRUCTURAL,
    MutationCategory.ROUTING_CHANGE: MutationLevel.STRUCTURAL,
    MutationCategory.SCHEMA_MIGRATION: MutationLevel.STRUCTURAL,

    # Level 3
    MutationCategory.MONOLITH_TO_MICROSERVICE: MutationLevel.ARCHITECTURAL,
    MutationCategory.REST_TO_EVENT_DRIVEN: MutationLevel.ARCHITECTURAL,
    MutationCategory.SYNC_TO_ASYNC: MutationLevel.ARCHITECTURAL,
    MutationCategory.SQL_TO_NOSQL: MutationLevel.ARCHITECTURAL,
    MutationCategory.FRAMEWORK_SWAP: MutationLevel.ARCHITECTURAL,
    MutationCategory.RENDERING_PARADIGM_CHANGE: MutationLevel.ARCHITECTURAL,
}


def get_mutation_level(category: MutationCategory) -> MutationLevel:
    """Get the mutation level for a category. Deterministic."""
    return _CATEGORY_LEVELS[category]


def is_true_mutation(category: MutationCategory) -> bool:
    """Only Level 2+ is a real mutation. Everything else is a gradient step."""
    return get_mutation_level(category) >= MutationLevel.STRUCTURAL


# ═══════════════════════════════════════════════════════════════
# MUTATION TRIGGER CONDITION
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class StagnationSignal:
    """
    Trigger condition for mutation.

    Mutation ONLY fires when:
        ΔL ≈ 0 for N iterations AND L > 0

    This is the ONLY legal trigger. No other condition may
    invoke a true mutation.
    """
    is_stagnant: bool
    loss_values: List[float]
    delta_l: float              # max |L_t - L_{t-1}| over window
    iterations_stagnant: int
    current_loss: float


def detect_stagnation(
    loss_history: List[float],
    window: int = 3,
    delta_threshold: float = 0.01,
) -> StagnationSignal:
    """
    Detect loss plateau.

    Stagnation = ΔL < threshold for `window` consecutive iterations
                 AND current loss > 0.

    Args:
        loss_history: Chronological loss values
        window: How many consecutive flat iterations trigger stagnation
        delta_threshold: Maximum ΔL to consider "flat"

    Returns:
        StagnationSignal with diagnosis
    """
    if len(loss_history) < window + 1:
        return StagnationSignal(
            is_stagnant=False,
            loss_values=loss_history,
            delta_l=float("inf"),
            iterations_stagnant=0,
            current_loss=loss_history[-1] if loss_history else 0.0,
        )

    recent = loss_history[-(window + 1):]
    deltas = [abs(recent[i] - recent[i - 1]) for i in range(1, len(recent))]
    max_delta = max(deltas)
    current_loss = loss_history[-1]

    stagnant_count = 0
    for d in reversed(deltas):
        if d < delta_threshold:
            stagnant_count += 1
        else:
            break

    is_stagnant = (stagnant_count >= window) and (current_loss > 0.0)

    return StagnationSignal(
        is_stagnant=is_stagnant,
        loss_values=recent,
        delta_l=max_delta,
        iterations_stagnant=stagnant_count,
        current_loss=current_loss,
    )


def select_mutation_level(stagnation: StagnationSignal) -> MutationLevel:
    """
    Select mutation level based on stagnation severity.

    Rules:
    - Not stagnant → GRADIENT (no mutation)
    - Stagnant 3-5 iterations → STRUCTURAL
    - Stagnant 6+ iterations → ARCHITECTURAL

    These thresholds are explicit, not learned.
    """
    if not stagnation.is_stagnant:
        return MutationLevel.GRADIENT

    if stagnation.iterations_stagnant >= 6:
        return MutationLevel.ARCHITECTURAL

    return MutationLevel.STRUCTURAL


# ═══════════════════════════════════════════════════════════════
# MUTATION DISTANCE ENFORCEMENT
# ═══════════════════════════════════════════════════════════════

class FakeMutationError(Exception):
    """
    Raised when a mutation does not actually change the state topology.

    This means distance(Φ(V_next), Φ(V_t)) <= threshold,
    which means the "mutation" was cosmetic, not structural.
    """

    def __init__(self, distance: float, threshold: float):
        self.distance = distance
        self.threshold = threshold
        super().__init__(
            f"FAKE MUTATION: distance={distance:.4f} <= threshold={threshold:.4f}. "
            f"Mutation did not change the state topology."
        )


def compute_fingerprint_distance(
    fp_current: str,
    fp_next: str,
) -> float:
    """
    Compute normalized Hamming distance between two fingerprint hashes.

    Returns a value in [0.0, 1.0]:
    - 0.0 = identical states (mutation failed)
    - 1.0 = maximally different states

    For SHA-256: compare hex characters.
    """
    if len(fp_current) != len(fp_next):
        return 1.0  # Different lengths = definitely different

    if fp_current == fp_next:
        return 0.0

    differences = sum(1 for a, b in zip(fp_current, fp_next) if a != b)
    return differences / len(fp_current)


def enforce_mutation_distance(
    fp_current: str,
    fp_next: str,
    minimum_distance: float = 0.1,
) -> float:
    """
    Verify that a mutation actually changed the state.

    Args:
        fp_current: Φ(V_t) before mutation
        fp_next: Φ(V_{t+1}) after mutation
        minimum_distance: Minimum required distance

    Returns:
        The computed distance

    Raises:
        FakeMutationError if distance <= minimum_distance
    """
    distance = compute_fingerprint_distance(fp_current, fp_next)

    if distance <= minimum_distance:
        raise FakeMutationError(distance, minimum_distance)

    return distance


# ═══════════════════════════════════════════════════════════════
# MUTATION RECORD
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class MutationRecord:
    """
    Immutable record of a mutation event.

    This is what gets logged. Not advice — data.
    """
    timestamp: float
    iteration: int
    level: MutationLevel
    category: MutationCategory
    trigger: StagnationSignal
    fp_before: str
    fp_after: str
    distance: float
    success: bool
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "iteration": self.iteration,
            "level": self.level.name,
            "category": self.category.value,
            "stagnant_iterations": self.trigger.iterations_stagnant,
            "delta_l": self.trigger.delta_l,
            "current_loss": self.trigger.current_loss,
            "fp_before": self.fp_before[:16],
            "fp_after": self.fp_after[:16],
            "distance": self.distance,
            "success": self.success,
            "reason": self.reason,
        }
