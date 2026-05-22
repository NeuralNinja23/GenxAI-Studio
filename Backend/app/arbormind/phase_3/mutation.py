# mutation.py
#
# Phase 3 Mutation Engine — execution layer above mutation_law.py
#
# RESPONSIBILITIES:
#   - Accept a MutationRequest (intent + stagnation context)
#   - Validate the request through MutationLaw
#   - Apply the mutation via directive pivot
#   - Return a MutationResult with distance proof
#
# HARD CONSTRAINTS (enforced, not advisory):
#   - Mutation ONLY fires when MutationLevel >= STRUCTURAL
#   - Mutation MUST change topology (FakeMutationError if not)
#   - This module does NOT retry, does NOT select branches,
#     does NOT override StateGate decisions

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

from app.arbormind.phase_3.mutation_law import (
    MutationLevel,
    MutationCategory,
    StagnationSignal,
    MutationRecord,
    detect_stagnation,
    select_mutation_level,
    enforce_mutation_distance,
    compute_fingerprint_distance,
    FakeMutationError,
)


# ═══════════════════════════════════════════════════════════════
# REQUEST
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class MutationRequest:
    """
    Input to the MutationEngine.

    Carries:
    - loss_history: chronological list of loss values (required for stagnation check)
    - fp_current: Φ(V_t) — fingerprint of the current state before mutation
    - fp_previous: Φ(V_{t-1}) — fingerprint of the prior state (for distance check)
    - iteration: current iteration number (for record keeping)
    - step_name: workflow step context

    This is a VALUE OBJECT. It carries data only.
    """
    loss_history: List[float]
    fp_current: str
    iteration: int
    step_name: str
    fp_previous: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════
# RESULT
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class MutationResult:
    """
    Output from the MutationEngine.

    Carries:
    - triggered: whether mutation was triggered at all
    - level: the mutation level selected (GRADIENT = no mutation)
    - category: the concrete mutation category applied
    - stagnation: the stagnation diagnosis that triggered it
    - record: immutable audit record (if triggered)
    - distance: fingerprint distance achieved (if measured)
    - error: populated if a FakeMutationError was raised

    This is a VALUE OBJECT. It carries data only.
    """
    triggered: bool
    level: MutationLevel
    stagnation: StagnationSignal
    record: Optional[MutationRecord] = None
    distance: Optional[float] = None
    error: Optional[str] = None

    @property
    def is_true_mutation(self) -> bool:
        """True only if a real structural topology change occurred."""
        return self.triggered and self.level >= MutationLevel.STRUCTURAL

    @property
    def succeeded(self) -> bool:
        """True if mutation triggered AND no FakeMutationError was raised."""
        return self.is_true_mutation and self.error is None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "triggered": self.triggered,
            "level": self.level.name,
            "stagnant_iterations": self.stagnation.iterations_stagnant,
            "delta_l": self.stagnation.delta_l,
            "distance": self.distance,
            "error": self.error,
            "succeeded": self.succeeded,
        }


# ═══════════════════════════════════════════════════════════════
# ENGINE
# ═══════════════════════════════════════════════════════════════

class MutationEngine:
    """
    Applies MutationLaw to decide whether and how to mutate.

    This engine:
    - NEVER selects cognitive branches
    - NEVER overrides StateGate or FailureMemory
    - NEVER retries executions
    - NEVER invents new mutation categories

    It ONLY:
    1. Detects stagnation from loss_history
    2. Selects the minimum legal mutation level
    3. Verifies that the mutation changed topology (distance check)
    4. Returns an immutable MutationResult

    The caller (ArborMindOrchestrator) decides what to DO with the result.
    This engine only computes and reports.
    """

    def __init__(
        self,
        stagnation_window: int = 3,
        delta_threshold: float = 0.01,
        minimum_mutation_distance: float = 0.05,
    ):
        self._stagnation_window = stagnation_window
        self._delta_threshold = delta_threshold
        self._min_distance = minimum_mutation_distance

    def evaluate(self, request: MutationRequest) -> MutationResult:
        """
        Evaluate whether a mutation should fire for the given request.

        Returns a MutationResult regardless of whether mutation is triggered.
        When triggered=False, the result still carries the stagnation diagnosis.

        Args:
            request: MutationRequest with loss history and fingerprint context

        Returns:
            MutationResult — always non-None, immutable
        """
        # ── Step 1: Detect stagnation ──
        stagnation = detect_stagnation(
            loss_history=request.loss_history,
            window=self._stagnation_window,
            delta_threshold=self._delta_threshold,
        )

        # ── Step 2: Select mutation level ──
        level = select_mutation_level(stagnation)

        # No true mutation required
        if level < MutationLevel.STRUCTURAL:
            return MutationResult(
                triggered=False,
                level=level,
                stagnation=stagnation,
            )

        # ── Step 3: Select concrete category at this level ──
        category = self._select_category(level)

        # ── Step 4: Distance verification (only if we have prev fingerprint) ──
        distance: Optional[float] = None
        error: Optional[str] = None
        record: Optional[MutationRecord] = None

        if request.fp_previous is not None:
            try:
                distance = enforce_mutation_distance(
                    fp_current=request.fp_previous,
                    fp_next=request.fp_current,
                    minimum_distance=self._min_distance,
                )
            except FakeMutationError as e:
                error = str(e)
                distance = e.distance
        else:
            # No previous fingerprint — assume topology changed (first mutation)
            distance = compute_fingerprint_distance(
                request.fp_current,
                request.fp_current[::-1],  # Self-distance for baseline
            )

        # ── Step 5: Build immutable record ──
        record = MutationRecord(
            timestamp=time.time(),
            iteration=request.iteration,
            level=level,
            category=category,
            trigger=stagnation,
            fp_before=request.fp_previous or "",
            fp_after=request.fp_current,
            distance=distance if distance is not None else 0.0,
            success=error is None,
            reason=error or f"Topology mutation at level {level.name}",
        )

        return MutationResult(
            triggered=True,
            level=level,
            stagnation=stagnation,
            record=record,
            distance=distance,
            error=error,
        )

    def _select_category(self, level: MutationLevel) -> MutationCategory:
        """
        Select the default mutation category for a given level.

        These are deterministic defaults — not random, not learned.
        The caller may override based on domain context.
        """
        if level >= MutationLevel.ARCHITECTURAL:
            return MutationCategory.FRAMEWORK_SWAP
        else:
            return MutationCategory.API_REDESIGN
