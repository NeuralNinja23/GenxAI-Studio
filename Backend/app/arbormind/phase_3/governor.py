# governor.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Set

from app.arbormind.phase_2.cognitive_directive import CognitiveDirective
from app.arbormind.phase_2.mutation_authority import MutationDimension


@dataclass(frozen=True)
class GovernanceVerdict:
    allowed: bool
    reason: str


class CognitiveGovernor:
    """
    Enforces Phase 2 constraints during Phase 3 reasoning.

    This governor:
    - cannot override Phase 1 halts
    - cannot retry
    - cannot invent permissions
    - cannot mutate state
    """

    def allow_mutation(
        self,
        requested: Set[MutationDimension],
        directive: CognitiveDirective,
    ) -> GovernanceVerdict:
        forbidden = set(directive.forbidden_mutations)

        illegal = requested & forbidden
        if illegal:
            return GovernanceVerdict(
                allowed=False,
                reason=f"Forbidden mutation dimensions requested: {sorted(d.value for d in illegal)}",
            )

        allowed_set = set(directive.allowed_mutations)
        if not requested.issubset(allowed_set):
            return GovernanceVerdict(
                allowed=False,
                reason="Requested mutation exceeds permitted dimensions",
            )

        return GovernanceVerdict(
            allowed=True,
            reason="Mutation request conforms to cognitive directive",
        )

    def allow_reasoning_pattern(
        self,
        pattern: str,
        directive: CognitiveDirective,
    ) -> GovernanceVerdict:
        if pattern in directive.avoid_patterns:
            return GovernanceVerdict(
                allowed=False,
                reason=f"Reasoning pattern explicitly forbidden: {pattern}",
            )

        return GovernanceVerdict(
            allowed=True,
            reason="Reasoning pattern permitted",
        )
