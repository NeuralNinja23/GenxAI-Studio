# state_gate.py
#
# ROLE: ENFORCE ONLY.
#
# Before ANY state is executed, it MUST pass through this gate.
# This gate reads the forbidden set from FailureMemory.
# This gate does NOT store failure metadata.
#
# FailureMemory = RECORD (what failed, why, when)
# StateGate = ENFORCE (is this state allowed to execute?)
#
# One source of truth. One enforcement layer.

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .failure_memory import FailureMemory


class ForbiddenStateError(Exception):
    """
    Raised when the system attempts to execute a state
    whose canonical fingerprint already exists in the failure set.

    This is NOT catchable in normal control flow.
    It represents a violation of ArborMind's core invariant:
        ∀ Φ(V_t) ∈ F: execution(V_t) is ILLEGAL.
    """

    def __init__(self, fingerprint: str, reason: str = ""):
        self.fingerprint = fingerprint
        super().__init__(
            f"FORBIDDEN STATE: Φ={fingerprint[:16]}... "
            f"already exists in failure set. {reason}"
        )


class DivergenceViolationError(Exception):
    """
    Raised when a new state fails to diverge from the previous state.

    This means Φ(V_{t+1}) == Φ(V_t), which is structurally identical
    to a retry. ArborMind does not retry. Ever.
    """

    def __init__(self, fingerprint: str):
        self.fingerprint = fingerprint
        super().__init__(
            f"DIVERGENCE VIOLATION: Φ(V_next)={fingerprint[:16]}... "
            f"is identical to Φ(V_current). This is a retry, not a mutation."
        )


class StateGate:
    """
    Global pre-execution gate.

    READS from FailureMemory to determine forbidden states.
    Does NOT store failure data itself.

    Contract:
    - ONE call to check() before every execution
    - If check() raises, execution MUST NOT proceed
    - No fallback, no degraded mode, no "try anyway"

    Invariants enforced:
    1. No state with a known-failed fingerprint may execute
       (forbidden set lives in FailureMemory)
    2. Every new state must be structurally different from the prior state

    If either invariant is violated, the system crashes.
    """

    def __init__(self, failure_memory: FailureMemory) -> None:
        self._failure_memory = failure_memory
        self._last_fingerprint: str | None = None
        self._total_checks: int = 0
        self._total_blocks: int = 0

    # ─────────────────────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────────────────────

    def check(self, fingerprint: str) -> None:
        """
        Gate a state for execution.

        Args:
            fingerprint: Canonical fingerprint Φ(V) of the state to execute.

        Raises:
            ForbiddenStateError: If fingerprint is in FailureMemory's forbidden set.
            DivergenceViolationError: If fingerprint == last executed fingerprint.
        """
        self._total_checks += 1

        # Invariant 1: No repeated failures
        # Source of truth: FailureMemory (RECORD layer)
        if self._failure_memory.is_forbidden(fingerprint):
            self._total_blocks += 1
            raise ForbiddenStateError(
                fingerprint,
                reason=f"Blocked {self._total_blocks}/{self._total_checks} total checks."
            )

        # Invariant 2: Every new state must diverge
        if self._last_fingerprint is not None and fingerprint == self._last_fingerprint:
            self._total_blocks += 1
            raise DivergenceViolationError(fingerprint)

    def record_execution(self, fingerprint: str) -> None:
        """
        Record that a state was executed.
        Call this AFTER successful check() and BEFORE actual execution.
        """
        self._last_fingerprint = fingerprint

    def assert_divergence(
        self,
        current_fingerprint: str,
        next_fingerprint: str,
    ) -> None:
        """
        Hard assertion: V_next is structurally different from V_current.

        Raises:
            DivergenceViolationError if Φ(V_next) == Φ(V_current)
        """
        if current_fingerprint == next_fingerprint:
            raise DivergenceViolationError(next_fingerprint)

    # ─────────────────────────────────────────────────────────
    # DIAGNOSTICS (read-only)
    # ─────────────────────────────────────────────────────────

    @property
    def forbidden_count(self) -> int:
        """Delegates to FailureMemory — single source of truth."""
        return self._failure_memory.count

    @property
    def total_checks(self) -> int:
        return self._total_checks

    @property
    def total_blocks(self) -> int:
        return self._total_blocks

    @property
    def block_rate(self) -> float:
        if self._total_checks == 0:
            return 0.0
        return self._total_blocks / self._total_checks

    def contains(self, fingerprint: str) -> bool:
        """Delegates to FailureMemory — single source of truth."""
        return self._failure_memory.is_forbidden(fingerprint)
