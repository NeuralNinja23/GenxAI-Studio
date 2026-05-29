# app/sentinel/topology/projection_metrics.py
"""
V4 Projection Instrumentation Metrics — Phase 9: Observability Core

Centralized real-time metric tracking for the AST projection pipeline
and bounded cognition engine.

Tracked metrics:
    - node_survival_rate        (% of nodes that successfully projected)
    - projection_survival_rate  (% of files that wrote without error)
    - stabilization_success_rate(% of stabilization attempts that converged)
    - branch_density            (total active branches per cycle)
    - ui_node_count             (count of UI_NODE types in the graph)
    - reflection_retries        (total critique-mutate retries)
    - entropy_per_branch        (dict of branch_id → entropy value)
    - failed_projections        (list of {file, error, traceback} dicts)

Usage:
    from app.sentinel.topology.projection_metrics import ProjectionMetrics

    metrics = ProjectionMetrics.get_instance()
    metrics.reset()
    metrics.record_node_attempt("DashboardView")
    metrics.record_node_success("DashboardView")
    metrics.record_projection_failure("Frontend/src/components/Chart.tsx", error, tb)
    summary = metrics.summary()
"""

import threading
import traceback
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ProjectionFailure:
    """Captures a single failed projection with full diagnostic context."""
    file_path: str
    error_class: str
    error_message: str
    traceback_str: str
    node_id: Optional[str] = None


class ProjectionMetrics:
    """
    Thread-safe, process-wide singleton for projection cycle instrumentation.

    All counters reset at the start of each projection cycle via ``reset()``.
    Downstream consumers should call ``summary()`` at cycle end for a
    complete observability snapshot.
    """

    _instance: Optional["ProjectionMetrics"] = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self) -> None:
        self._cycle_lock = threading.Lock()
        self.reset()

    @classmethod
    def get_instance(cls) -> "ProjectionMetrics":
        """Return the process-wide singleton."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = ProjectionMetrics()
        return cls._instance

    def reset(self) -> None:
        """Reset all counters for a new projection cycle."""
        with self._cycle_lock:
            # Node-level tracking
            self._nodes_attempted: int = 0
            self._nodes_succeeded: int = 0
            self._node_ids_attempted: List[str] = []
            self._node_ids_succeeded: List[str] = []

            # Projection (file-level) tracking
            self._projections_attempted: int = 0
            self._projections_succeeded: int = 0
            self._failed_projections: List[ProjectionFailure] = []

            # Stabilization tracking
            self._stabilization_attempts: int = 0
            self._stabilization_successes: int = 0

            # Branch-level tracking
            self._branch_density: int = 0
            self._ui_node_count: int = 0
            self._reflection_retries: int = 0
            self._entropy_per_branch: Dict[str, float] = {}

    # ─────────────────────────────────────────────────────────
    # Node-level recording
    # ─────────────────────────────────────────────────────────

    def record_node_attempt(self, node_id: str) -> None:
        with self._cycle_lock:
            self._nodes_attempted += 1
            self._node_ids_attempted.append(node_id)

    def record_node_success(self, node_id: str) -> None:
        with self._cycle_lock:
            self._nodes_succeeded += 1
            self._node_ids_succeeded.append(node_id)

    # ─────────────────────────────────────────────────────────
    # Projection (file-level) recording
    # ─────────────────────────────────────────────────────────

    def record_projection_attempt(self, file_path: str) -> None:
        with self._cycle_lock:
            self._projections_attempted += 1

    def record_projection_success(self, file_path: str) -> None:
        with self._cycle_lock:
            self._projections_succeeded += 1

    def record_projection_failure(
        self,
        file_path: str,
        error: Exception,
        node_id: Optional[str] = None,
    ) -> None:
        with self._cycle_lock:
            tb_str = "".join(traceback.format_exception(type(error), error, error.__traceback__))
            self._failed_projections.append(ProjectionFailure(
                file_path=file_path,
                error_class=type(error).__name__,
                error_message=str(error),
                traceback_str=tb_str,
                node_id=node_id,
            ))

    # ─────────────────────────────────────────────────────────
    # Stabilization recording
    # ─────────────────────────────────────────────────────────

    def record_stabilization_attempt(self) -> None:
        with self._cycle_lock:
            self._stabilization_attempts += 1

    def record_stabilization_success(self) -> None:
        with self._cycle_lock:
            self._stabilization_successes += 1

    # ─────────────────────────────────────────────────────────
    # Branch / cognition recording
    # ─────────────────────────────────────────────────────────

    def set_branch_density(self, count: int) -> None:
        with self._cycle_lock:
            self._branch_density = count

    def set_ui_node_count(self, count: int) -> None:
        with self._cycle_lock:
            self._ui_node_count = count

    def increment_reflection_retries(self) -> None:
        with self._cycle_lock:
            self._reflection_retries += 1

    def record_branch_entropy(self, branch_id: str, entropy: float) -> None:
        with self._cycle_lock:
            self._entropy_per_branch[branch_id] = entropy

    # ─────────────────────────────────────────────────────────
    # Summary
    # ─────────────────────────────────────────────────────────

    def summary(self) -> Dict[str, Any]:
        """
        Return a complete observability snapshot for the current cycle.
        """
        with self._cycle_lock:
            node_survival = (
                (self._nodes_succeeded / self._nodes_attempted * 100.0)
                if self._nodes_attempted > 0 else 100.0
            )
            proj_survival = (
                (self._projections_succeeded / self._projections_attempted * 100.0)
                if self._projections_attempted > 0 else 100.0
            )
            stab_success = (
                (self._stabilization_successes / self._stabilization_attempts * 100.0)
                if self._stabilization_attempts > 0 else 100.0
            )

            return {
                # Survival rates (percentages)
                "node_survival_rate": round(node_survival, 2),
                "projection_survival_rate": round(proj_survival, 2),
                "stabilization_success_rate": round(stab_success, 2),

                # Counts
                "nodes_attempted": self._nodes_attempted,
                "nodes_succeeded": self._nodes_succeeded,
                "projections_attempted": self._projections_attempted,
                "projections_succeeded": self._projections_succeeded,

                # Branch metrics
                "branch_density": self._branch_density,
                "ui_node_count": self._ui_node_count,
                "reflection_retries": self._reflection_retries,
                "entropy_per_branch": dict(self._entropy_per_branch),

                # Failure diagnostics
                "failed_projections": [
                    {
                        "file": f.file_path,
                        "error_class": f.error_class,
                        "error": f.error_message,
                        "traceback": f.traceback_str,
                        "node_id": f.node_id,
                    }
                    for f in self._failed_projections
                ],

                # Dropped nodes (attempted but not succeeded)
                "dropped_nodes": [
                    nid for nid in self._node_ids_attempted
                    if nid not in self._node_ids_succeeded
                ],
            }
