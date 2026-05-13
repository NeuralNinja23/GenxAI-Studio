# attention.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict

from app.arbormind.phase_2.cognitive_directive import CognitiveDirective


@dataclass
class AttentionState:
    """
    Represents attention weights for cognitive branches.

    NOTE:
    - This structure does NOT enforce normalization
    - It does NOT decide outcomes
    - It only carries weighted signals forward
    """

    weights: Dict[str, float]


class AttentionRouter:
    """
    Applies Phase 2 cognitive directives to raw attention weights.

    This router:
    - never selects a branch
    - never mutates branches
    - never halts execution
    """

    def apply(
        self,
        base_attention: Dict[str, float],
        directive: CognitiveDirective,
    ) -> AttentionState:
        adjusted: Dict[str, float] = dict(base_attention)

        # ───────── APPLY PENALTIES ─────────
        for pattern, penalty in directive.attention_penalties.items():
            for branch_id, weight in adjusted.items():
                adjusted[branch_id] = weight + penalty

        # ───────── APPLY BOOSTS ─────────
        for pattern, boost in directive.attention_boosts.items():
            for branch_id, weight in adjusted.items():
                adjusted[branch_id] = weight + boost

        return AttentionState(weights=adjusted)
