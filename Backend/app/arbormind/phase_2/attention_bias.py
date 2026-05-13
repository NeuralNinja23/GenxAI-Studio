# attention_bias.py
#It only distorts attention weights based on remembered failure shapes.
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Set

from .failure_taxonomy import FailureClass, FailureDomain, FailureNature
from .mutation_authority import MutationPolicy, MutationDimension


# ─────────────────────────────────────────────────────────────
# Attention Bias Signal
# ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AttentionBias:
    """
    Pure bias signal.

    Positive values boost attention.
    Negative values penalize attention.

    No normalization.
    No clipping.
    No enforcement.
    """

    boosts: Dict[str, float] = field(default_factory=dict)
    penalties: Dict[str, float] = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────
# Attention Bias Engine
# ─────────────────────────────────────────────────────────────

class AttentionBiasEngine:
    """
    Generates attention biases from failure cognition.

    IMPORTANT:
    - This engine does NOT know about branches
    - It does NOT score options
    - It does NOT enforce decisions

    It only emits *directional pressure*
    """

    def derive(
        self,
        failure: FailureClass,
        mutation_policy: MutationPolicy,
    ) -> AttentionBias:
        boosts: Dict[str, float] = {}
        penalties: Dict[str, float] = {}

        # ───────── DOMAIN-BASED BIAS ─────────

        if failure.domain == FailureDomain.LOGIC:
            penalties["semantic_drift"] = -0.8
            penalties["creative_reframing"] = -0.6
            boosts["structural_clarity"] = +0.6
            boosts["procedural_discipline"] = +0.4

        elif failure.domain == FailureDomain.STRUCTURE:
            penalties["reordering_instability"] = -0.6
            boosts["hierarchical_decomposition"] = +0.5

        elif failure.domain == FailureDomain.SPECIFICATION:
            penalties["assumption_injection"] = -1.0
            boosts["clarification_request"] = +0.7

        elif failure.domain == FailureDomain.KNOWLEDGE:
            penalties["hallucinated_facts"] = -1.0
            boosts["explicit_unknowns"] = +0.8

        elif failure.domain == FailureDomain.CAPABILITY:
            penalties["capability_bypass"] = -1.0
            boosts["capability_alignment"] = +0.6

        # ───────── NATURE-BASED BIAS ─────────

        if failure.nature == FailureNature.COLLAPSE:
            penalties["branch_depth"] = -0.9
            penalties["parallel_expansion"] = -0.7
            boosts["single_path_reasoning"] = +0.6

        if failure.nature == FailureNature.INVALID:
            penalties["speculative_steps"] = -0.6
            boosts["constraint_validation"] = +0.5

        # ───────── MUTATION-BASED SUPPRESSION ─────────

        for dim in mutation_policy.forbidden:
            penalties[f"mutation:{dim.value}"] = -1.0

        for dim in mutation_policy.allowed:
            if dim != MutationDimension.NONE:
                boosts[f"mutation:{dim.value}"] = +0.3

        return AttentionBias(
            boosts=boosts,
            penalties=penalties,
        )
