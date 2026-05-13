# cognitive_directive.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List

from .mutation_authority import MutationDimension


@dataclass(frozen=True)
class CognitiveDirective:
    """
    Immutable cognitive constraints passed to future reasoning phases.

    This object:
    - does NOT decide
    - does NOT execute
    - does NOT mutate

    It constrains *how thinking may proceed*.
    """

    avoid_patterns: List[str] = field(default_factory=list)
    prefer_patterns: List[str] = field(default_factory=list)

    allowed_mutations: List[MutationDimension] = field(default_factory=list)
    forbidden_mutations: List[MutationDimension] = field(default_factory=list)

    attention_boosts: Dict[str, float] = field(default_factory=dict)
    attention_penalties: Dict[str, float] = field(default_factory=dict)


def force_architectural_pivot(
    directive: CognitiveDirective,
) -> CognitiveDirective:
    """
    Generates a forced mutation directive that repels the current reasoning mode.
    """

    dominant = directive.allowed_mutations[:1] if directive.allowed_mutations else []

    forbidden = set(directive.forbidden_mutations)
    forbidden.update(dominant)

    # Force STRUCTURAL mutation if not already forbidden
    forced_allowed = [MutationDimension.STRUCTURAL]

    return CognitiveDirective(
        avoid_patterns=directive.avoid_patterns,
        prefer_patterns=directive.prefer_patterns,
        allowed_mutations=forced_allowed,
        forbidden_mutations=list(forbidden),
        attention_boosts={
            **directive.attention_boosts,
            "architectural_pivot": 1.0,
        },
        attention_penalties={
            **directive.attention_penalties,
            "stagnant_reasoning": 1.0,
        },
    )
