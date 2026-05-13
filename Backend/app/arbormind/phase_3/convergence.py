# convergence.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from .validity import ValidityEvaluator, ValidityResult
from .attention import AttentionState


@dataclass(frozen=True)
class ConvergenceResult:
    resolved: bool
    selected_branch_id: str | None
    reason: str
    metadata: Dict[str, Any]


class ConvergenceEngine:
    """
    Resolves grounded cognitive branches into a single outcome.
    """

    def __init__(self, validator: ValidityEvaluator):
        self._validator = validator

    def converge(
        self,
        branches: Dict[str, Dict[str, Any]],
        attention: AttentionState,
        evidences: Optional[Dict[str, Any]] = None,
    ) -> ConvergenceResult:
        """
        Grounded convergence.
        """
        valid_branches: Dict[str, float] = {}
        evidences = evidences or {}

        # ───────── EPISTEMIC FILTER ─────────
        for branch_id, payload in branches.items():
            evidence = evidences.get(branch_id)
            validity: ValidityResult = self._validator.evaluate(payload, evidence)
            
            if validity.valid:
                weight = attention.weights.get(branch_id, 0.0)
                valid_branches[branch_id] = weight

        if not valid_branches:
            return ConvergenceResult(
                resolved=False,
                selected_branch_id=None,
                reason="All cognitive branches failed epistemic grounding",
                metadata={"stage": "validity"},
            )

        # ───────── SELECTION (Attention Weighted) ─────────
        selected_branch_id = max(
            valid_branches,
            key=lambda bid: valid_branches[bid],
        )

        return ConvergenceResult(
            resolved=True,
            selected_branch_id=selected_branch_id,
            reason="Branch selected via grounded convergence",
            metadata={
                "candidate_count": len(valid_branches),
                "stagnation_risk": 0.0, # Placeholder
            },
        )
