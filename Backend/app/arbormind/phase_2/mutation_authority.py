# mutation_authority.py

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Set

from .failure_taxonomy import (
    FailureClass,
    FailureDomain,
    FailureNature,
    FailureRecoverability,
)


# ─────────────────────────────────────────────────────────────
# Mutation Dimensions (orthogonal)
# ─────────────────────────────────────────────────────────────

class MutationDimension(str, Enum):
    SEMANTIC = "semantic"        # meaning, framing, interpretation
    STRUCTURAL = "structural"    # ordering, decomposition, architecture
    PROCEDURAL = "procedural"    # step sequencing, strategy
    HEURISTIC = "heuristic"      # search / exploration bias
    AESTHETIC = "aesthetic"      # style only (never correctness)
    NONE = "none"


# ─────────────────────────────────────────────────────────────
# Mutation Permission Result
# ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class MutationPolicy:
    allowed: Set[MutationDimension]
    forbidden: Set[MutationDimension]

    @property
    def is_mutation_allowed(self) -> bool:
        return bool(self.allowed) and MutationDimension.NONE not in self.allowed


# ─────────────────────────────────────────────────────────────
# Mutation Authority
# ─────────────────────────────────────────────────────────────

class MutationAuthority:
    """
    Determines which mutation dimensions are *legally permitted*
    for a given FailureClass.

    This class:
    - does NOT perform mutation
    - does NOT rank mutations
    - does NOT override execution outcomes

    It defines *epistemic boundaries* only.
    """

    def decide(self, failure: FailureClass) -> MutationPolicy:
        # ───────── TERMINAL / NON-RECOVERABLE ─────────
        if failure.recoverability == FailureRecoverability.NON_RECOVERABLE:
            return MutationPolicy(
                allowed={MutationDimension.NONE},
                forbidden=set(MutationDimension) - {MutationDimension.NONE},
            )

        # ───────── REQUIRES EXTERNAL INPUT ─────────
        if failure.recoverability == FailureRecoverability.REQUIRES_EXTERNAL:
            # Mutation cannot substitute missing truth or authority
            return MutationPolicy(
                allowed={MutationDimension.AESTHETIC},
                forbidden=set(MutationDimension) - {MutationDimension.AESTHETIC},
            )

        # ───────── MUTABLE FAILURES ─────────
        allowed: Set[MutationDimension] = set()
        forbidden: Set[MutationDimension] = set()

        # Domain-specific mutation law
        if failure.domain == FailureDomain.LOGIC:
            allowed |= {
                MutationDimension.STRUCTURAL,
                MutationDimension.PROCEDURAL,
            }
            forbidden |= {
                MutationDimension.SEMANTIC,   # truth cannot be redefined
                MutationDimension.HEURISTIC,
                MutationDimension.AESTHETIC,
            }

        elif failure.domain == FailureDomain.STRUCTURE:
            allowed |= {
                MutationDimension.STRUCTURAL,
                MutationDimension.PROCEDURAL,
            }
            forbidden |= {
                MutationDimension.SEMANTIC,
                MutationDimension.AESTHETIC,
            }

        elif failure.domain == FailureDomain.SPECIFICATION:
            # Specification failures are *not* solvable via mutation
            allowed |= {MutationDimension.AESTHETIC}
            forbidden |= {
                MutationDimension.SEMANTIC,
                MutationDimension.STRUCTURAL,
                MutationDimension.PROCEDURAL,
                MutationDimension.HEURISTIC,
            }

        elif failure.domain == FailureDomain.KNOWLEDGE:
            # You cannot invent missing knowledge
            allowed |= {MutationDimension.NONE}
            forbidden |= set(MutationDimension) - {MutationDimension.NONE}

        elif failure.domain == FailureDomain.CAPABILITY:
            # Capability limits cannot be mutated around
            allowed |= {MutationDimension.NONE}
            forbidden |= set(MutationDimension) - {MutationDimension.NONE}

        else:
            # UNKNOWN defaults to conservative
            allowed |= {MutationDimension.NONE}
            forbidden |= set(MutationDimension) - {MutationDimension.NONE}

        # ───────── Nature-based overrides ─────────
        if failure.nature in {FailureNature.COLLAPSE, FailureNature.INVALID}:
            forbidden |= allowed
            allowed = {MutationDimension.NONE}

        return MutationPolicy(
            allowed=allowed,
            forbidden=forbidden,
        )
