# convergence_ledger.py
#
# STEP 4: Measurable truth.
#
# No metrics = no truth.
# This module logs EVERY iteration's state so you can
# diagnose whether ArborMind is a control system or a fancy retry loop.
#
# Four metrics, measured every iteration:
#   1. Loss curve         — is L decreasing?
#   2. Failure uniqueness — are we repeating failures?
#   3. Convergence time   — how fast do we reach Ω?
#   4. Repulsion effectiveness — are new states far from old failures?

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import time
import json


# ═══════════════════════════════════════════════════════════════
# ITERATION SNAPSHOT
# ═══════════════════════════════════════════════════════════════

@dataclass
class IterationSnapshot:
    """
    Complete state of one iteration.
    Every field is measured, not estimated.
    """
    iteration: int
    timestamp: float

    # Loss
    loss: float
    loss_delta: float                   # L_t - L_{t-1}

    # Fingerprint
    fingerprint: str
    fingerprint_is_novel: bool          # Never seen before?

    # Failure set state
    total_unique_failures: int
    total_failure_observations: int

    # Repulsion
    min_distance_to_failure_set: float  # How far is current state from nearest failure?
    avg_distance_to_failure_set: float

    # Mutation (if any)
    mutation_applied: bool
    mutation_level: Optional[str] = None
    mutation_category: Optional[str] = None
    mutation_distance: Optional[float] = None

    # Convergence
    attention_delta: float = 0.0        # max |α_t - α_{t-1}|
    converged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "t": self.iteration,
            "ts": self.timestamp,
            "L": self.loss,
            "ΔL": self.loss_delta,
            "Φ": self.fingerprint[:16],
            "novel": self.fingerprint_is_novel,
            "F_unique": self.total_unique_failures,
            "F_total": self.total_failure_observations,
            "d_min": self.min_distance_to_failure_set,
            "d_avg": self.avg_distance_to_failure_set,
            "mutated": self.mutation_applied,
            "mut_level": self.mutation_level,
            "Δα": self.attention_delta,
            "Ω": self.converged,
        }


# ═══════════════════════════════════════════════════════════════
# CONVERGENCE LEDGER
# ═══════════════════════════════════════════════════════════════

class ConvergenceLedger:
    """
    Append-only log of iteration snapshots.

    This is the single source of truth for whether ArborMind
    is working or broken. Read the metrics. They don't lie.

    Diagnosis guide:
    ─────────────────────────────────────────────────────────
    Symptom                  │ Cause                │ Fix
    ─────────────────────────────────────────────────────────
    Same errors repeat       │ Φ is weak            │ Strengthen canonical_fingerprint
    Loss doesn't decrease    │ Control law broken    │ Fix attention/repulsion
    Random loss jumps        │ Mutation broken       │ Fix mutation triggers
    Stuck in loop            │ Retries still exist   │ Kill retry paths
    No convergence           │ Ω condition broken    │ Fix convergence detector
    ─────────────────────────────────────────────────────────
    """

    def __init__(self) -> None:
        self._snapshots: List[IterationSnapshot] = []
        self._seen_fingerprints: set[str] = set()
        self._failure_fingerprints: set[str] = set()
        self._total_failure_observations: int = 0
        self._start_time: float = time.time()

    # ─────────────────────────────────────────────────────────
    # RECORDING
    # ─────────────────────────────────────────────────────────

    def record(self, snapshot: IterationSnapshot) -> None:
        """Record one iteration. Append-only."""
        self._snapshots.append(snapshot)
        self._seen_fingerprints.add(snapshot.fingerprint)

    def record_failure(self, fingerprint: str) -> None:
        """Record a failure observation."""
        self._failure_fingerprints.add(fingerprint)
        self._total_failure_observations += 1

    # ─────────────────────────────────────────────────────────
    # METRIC 1: LOSS CURVE
    # ─────────────────────────────────────────────────────────

    @property
    def loss_curve(self) -> List[float]:
        """Raw loss values over time. Should be decreasing."""
        return [s.loss for s in self._snapshots]

    @property
    def loss_is_decreasing(self) -> bool:
        """
        True if loss trend is downward over the last 3 iterations.
        If NOT decreasing: system is broken.
        """
        curve = self.loss_curve
        if len(curve) < 3:
            return True  # Not enough data

        recent = curve[-3:]
        # At least 2 of 3 should be decreasing
        decreases = sum(
            1 for i in range(1, len(recent))
            if recent[i] < recent[i - 1]
        )
        return decreases >= 1

    @property
    def final_loss(self) -> float:
        if not self._snapshots:
            return float("inf")
        return self._snapshots[-1].loss

    # ─────────────────────────────────────────────────────────
    # METRIC 2: FAILURE UNIQUENESS
    # ─────────────────────────────────────────────────────────

    @property
    def unique_failure_count(self) -> int:
        return len(self._failure_fingerprints)

    @property
    def total_failure_observations(self) -> int:
        return self._total_failure_observations

    @property
    def novelty_rate(self) -> float:
        """
        unique_failures / total_failures.

        Should be HIGH (close to 1.0).
        If LOW: you're repeating failures. Φ is weak.
        """
        if self._total_failure_observations == 0:
            return 1.0
        return len(self._failure_fingerprints) / self._total_failure_observations

    # ─────────────────────────────────────────────────────────
    # METRIC 3: CONVERGENCE TIME
    # ─────────────────────────────────────────────────────────

    @property
    def total_iterations(self) -> int:
        return len(self._snapshots)

    @property
    def elapsed_seconds(self) -> float:
        return time.time() - self._start_time

    @property
    def convergence_iteration(self) -> Optional[int]:
        """Iteration number where Ω was first reached, or None."""
        for s in self._snapshots:
            if s.converged:
                return s.iteration
        return None

    @property
    def converged(self) -> bool:
        return self.convergence_iteration is not None

    # ─────────────────────────────────────────────────────────
    # METRIC 4: REPULSION EFFECTIVENESS
    # ─────────────────────────────────────────────────────────

    @property
    def repulsion_distances(self) -> List[float]:
        """
        min_distance_to_failure_set over time.
        Should INCREASE (states should get further from failures).
        """
        return [s.min_distance_to_failure_set for s in self._snapshots]

    @property
    def repulsion_is_effective(self) -> bool:
        """
        True if average distance to failure set is increasing.
        If False: attention/repulsion mechanism is broken.
        """
        distances = self.repulsion_distances
        if len(distances) < 3:
            return True  # Not enough data

        # Compare first half avg vs second half avg
        mid = len(distances) // 2
        first_half = distances[:mid]
        second_half = distances[mid:]

        avg_first = sum(first_half) / len(first_half) if first_half else 0
        avg_second = sum(second_half) / len(second_half) if second_half else 0

        return avg_second >= avg_first

    # ─────────────────────────────────────────────────────────
    # MUTATION STATS
    # ─────────────────────────────────────────────────────────

    @property
    def mutation_count(self) -> int:
        return sum(1 for s in self._snapshots if s.mutation_applied)

    @property
    def mutation_success_rate(self) -> float:
        """
        Of iterations AFTER mutation, how many saw loss decrease?
        """
        mutations = [
            i for i, s in enumerate(self._snapshots)
            if s.mutation_applied
        ]
        if not mutations:
            return 0.0

        successes = 0
        for idx in mutations:
            if idx + 1 < len(self._snapshots):
                if self._snapshots[idx + 1].loss < self._snapshots[idx].loss:
                    successes += 1

        return successes / len(mutations)

    # ─────────────────────────────────────────────────────────
    # DIAGNOSIS
    # ─────────────────────────────────────────────────────────

    def diagnose(self) -> Dict[str, Any]:
        """
        Full diagnostic summary.

        Read this after a run to know if ArborMind worked.
        """
        return {
            "iterations": self.total_iterations,
            "elapsed_s": round(self.elapsed_seconds, 2),
            "converged": self.converged,
            "convergence_iteration": self.convergence_iteration,
            "final_loss": self.final_loss,
            "loss_decreasing": self.loss_is_decreasing,
            "loss_curve": self.loss_curve,
            "unique_failures": self.unique_failure_count,
            "total_failure_observations": self.total_failure_observations,
            "novelty_rate": round(self.novelty_rate, 3),
            "repulsion_effective": self.repulsion_is_effective,
            "repulsion_distances": self.repulsion_distances,
            "mutations": self.mutation_count,
            "mutation_success_rate": round(self.mutation_success_rate, 3),
            # Verdict
            "verdict": self._verdict(),
        }

    def _verdict(self) -> str:
        """One-line system health verdict."""
        issues = []

        if self.total_iterations > 0 and not self.loss_is_decreasing:
            issues.append("loss_not_decreasing")

        if self.novelty_rate < 0.5:
            issues.append("repeating_failures")

        if not self.repulsion_is_effective:
            issues.append("repulsion_broken")

        if self.total_iterations > 5 and not self.converged:
            issues.append("no_convergence")

        if not issues:
            return "HEALTHY"

        return f"UNHEALTHY: {', '.join(issues)}"

    # ─────────────────────────────────────────────────────────
    # EXPORT
    # ─────────────────────────────────────────────────────────

    def to_json(self) -> str:
        """Export full ledger as JSON for external analysis."""
        return json.dumps({
            "diagnosis": self.diagnose(),
            "snapshots": [s.to_dict() for s in self._snapshots],
        }, indent=2)

    def to_log_lines(self) -> List[str]:
        """
        One-line-per-iteration log format for terminal output.

        Format:
        [t=1] L=3.20 ΔL=-0.50 Φ=a3f2... novel=✓ F=1/1 d_min=0.82 Ω=✗
        """
        lines = []
        for s in self._snapshots:
            novel = "✓" if s.fingerprint_is_novel else "✗"
            omega = "✓" if s.converged else "✗"
            mut = f" MUT={s.mutation_level}" if s.mutation_applied else ""
            lines.append(
                f"[t={s.iteration}] "
                f"L={s.loss:.2f} ΔL={s.loss_delta:+.2f} "
                f"Φ={s.fingerprint[:8]}.. "
                f"novel={novel} "
                f"F={s.total_unique_failures}/{s.total_failure_observations} "
                f"d_min={s.min_distance_to_failure_set:.2f} "
                f"Ω={omega}"
                f"{mut}"
            )
        return lines
