# convergence.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import hashlib

from .validity import ValidityEvaluator, ValidityResult
from .attention import AttentionState

@dataclass
class ConvergenceState:
    """
    State tracking for the ConvergenceKernel.
    Prevents stateless heuristics and oscillation.
    """
    total_cycles: int = 0
    stagnation_cycles: int = 0
    entropy_score: float = 0.0
    semantic_signature: str = "healthy"
    
    # State Transition History
    previous_loss: float = 0.0
    previous_mutation: Optional[str] = None
    previous_failure_class: Optional[str] = None
    state_transition_hash: str = ""
    
    def update_hash(self) -> None:
        """Computes a deterministic hash of the current state cycle to detect oscillation."""
        payload = f"{self.previous_loss}_{self.previous_mutation}_{self.previous_failure_class}_{self.semantic_signature}"
        self.state_transition_hash = hashlib.sha256(payload.encode()).hexdigest()[:16]

@dataclass(frozen=True)
class ConvergenceResult:
    resolved: bool
    selected_branch_id: str | None
    reason: str
    metadata: Dict[str, Any]

class ConvergenceKernel:
    """
    Governs long-horizon convergence.
    Replaces ConvergenceEngine. Uses state history to detect oscillation and force mutation.
    """

    def __init__(self, validator: ValidityEvaluator):
        self._validator = validator
        self.state = ConvergenceState()

    def converge(
        self,
        branches: Dict[str, Dict[str, Any]],
        attention: AttentionState,
        evidences: Optional[Dict[str, Any]] = None,
        current_loss: float = 0.0,
        primary_signature: str = "healthy"
    ) -> ConvergenceResult:
        """
        Grounded convergence with history tracking.
        """
        self.state.total_cycles += 1
        
        # 1. Update State History
        if self.state.previous_loss == current_loss and current_loss > 0:
            self.state.stagnation_cycles += 1
        else:
            self.state.stagnation_cycles = 0
            
        self.state.previous_loss = current_loss
        self.state.semantic_signature = primary_signature
        self.state.update_hash()

        # 2. Epistemic Filter
        valid_branches: Dict[str, float] = {}
        evidences = evidences or {}

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
                metadata={"stage": "validity", "state_hash": self.state.state_transition_hash},
            )

        # 3. Oscillation/Stagnation Detection
        if self.state.stagnation_cycles > 3:
            return ConvergenceResult(
                resolved=False,
                selected_branch_id=None,
                reason="Convergence Oscillation Detected. Forcing architectural mutation.",
                metadata={"stage": "governance", "stagnation": True, "state_hash": self.state.state_transition_hash}
            )

        # 4. Selection (Attention Weighted)
        selected_branch_id = max(
            valid_branches,
            key=lambda bid: valid_branches[bid],
        )

        return ConvergenceResult(
            resolved=True,
            selected_branch_id=selected_branch_id,
            reason="Branch selected via governed convergence",
            metadata={
                "candidate_count": len(valid_branches),
                "stagnation_risk": self.state.stagnation_cycles / 3.0,
                "state_hash": self.state.state_transition_hash
            },
        )

