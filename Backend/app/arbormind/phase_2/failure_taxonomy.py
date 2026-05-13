# failure_taxonomy.py

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Set

from app.arbormind.phase_1.state import FailureRecord, FailureSeverity


# ─────────────────────────────────────────────────────────────
# Taxonomy Axes (orthogonal, non-overlapping)
# ─────────────────────────────────────────────────────────────

class FailureDomain(str, Enum):
    SPECIFICATION = "specification"     # unclear, contradictory, underspecified intent
    LOGIC = "logic"                     # internally inconsistent reasoning
    KNOWLEDGE = "knowledge"             # missing / incorrect factual grounding
    STRUCTURE = "structure"             # invalid ordering / decomposition
    CAPABILITY = "capability"           # tool / model / system limitation
    EXECUTION = "execution"             # runtime or integration failure
    SAFETY = "safety"                   # policy / alignment violation
    UNKNOWN = "unknown"


class FailureNature(str, Enum):
    INCOMPLETE = "incomplete"           # something required is missing
    INCONSISTENT = "inconsistent"       # contradictions exist
    INVALID = "invalid"                 # violates hard constraints
    UNSUPPORTED = "unsupported"         # cannot be done with available means
    AMBIGUOUS = "ambiguous"             # multiple valid interpretations
    COLLAPSE = "collapse"               # reasoning degenerated / incoherent
    TERMINAL = "terminal"               # cannot be continued meaningfully


class FailureRecoverability(str, Enum):
    NON_RECOVERABLE = "non_recoverable" # mutation must NOT be attempted
    MUTABLE = "mutable"                 # reframing is allowed
    REQUIRES_EXTERNAL = "requires_external"  # needs new info, tools, or authority


# ─────────────────────────────────────────────────────────────
# Canonical Failure Class
# ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FailureClass:
    domain: FailureDomain
    nature: FailureNature
    recoverability: FailureRecoverability
    severity: FailureSeverity


# ─────────────────────────────────────────────────────────────
# Deterministic Mapping Rules
# ─────────────────────────────────────────────────────────────
#
# IMPORTANT:
# - No heuristics
# - No fuzzy matching
# - No statistical inference
# - Rules are explicit and inspectable
#

class FailureTaxonomy:
    """
    Maps raw FailureRecord → canonical FailureClass.

    This layer performs *classification only*.
    It does not decide actions, mutations, retries, or healing.
    """

    def classify(self, failure: FailureRecord) -> FailureClass:
        # Safety is always dominant
        if failure.severity == FailureSeverity.FATAL:
            return FailureClass(
                domain=FailureDomain.SAFETY,
                nature=FailureNature.TERMINAL,
                recoverability=FailureRecoverability.NON_RECOVERABLE,
                severity=failure.severity,
            )

        reason = failure.reason.lower()

        # ───────── SPECIFICATION FAILURES ─────────
        if "ambiguous" in reason or "unclear" in reason or "underspecified" in reason:
            return FailureClass(
                domain=FailureDomain.SPECIFICATION,
                nature=FailureNature.AMBIGUOUS,
                recoverability=FailureRecoverability.REQUIRES_EXTERNAL,
                severity=failure.severity,
            )

        # ───────── LOGIC FAILURES ─────────
        if "contradiction" in reason or "inconsistent" in reason:
            return FailureClass(
                domain=FailureDomain.LOGIC,
                nature=FailureNature.INCONSISTENT,
                recoverability=FailureRecoverability.MUTABLE,
                severity=failure.severity,
            )

        if "invalid reasoning" in reason or "logical collapse" in reason:
            return FailureClass(
                domain=FailureDomain.LOGIC,
                nature=FailureNature.COLLAPSE,
                recoverability=FailureRecoverability.NON_RECOVERABLE,
                severity=failure.severity,
            )

        # ───────── KNOWLEDGE FAILURES ─────────
        if "unknown" in reason or "missing knowledge" in reason:
            return FailureClass(
                domain=FailureDomain.KNOWLEDGE,
                nature=FailureNature.INCOMPLETE,
                recoverability=FailureRecoverability.REQUIRES_EXTERNAL,
                severity=failure.severity,
            )

        # ───────── STRUCTURE FAILURES ─────────
        if "ordering" in reason or "decomposition" in reason:
            return FailureClass(
                domain=FailureDomain.STRUCTURE,
                nature=FailureNature.INVALID,
                recoverability=FailureRecoverability.MUTABLE,
                severity=failure.severity,
            )

        # ───────── CAPABILITY FAILURES ─────────
        if "not supported" in reason or "capability" in reason:
            return FailureClass(
                domain=FailureDomain.CAPABILITY,
                nature=FailureNature.UNSUPPORTED,
                recoverability=FailureRecoverability.REQUIRES_EXTERNAL,
                severity=failure.severity,
            )

        # ───────── EXECUTION FAILURES ─────────
        if "runtime" in reason or "execution" in reason:
            return FailureClass(
                domain=FailureDomain.EXECUTION,
                nature=FailureNature.INVALID,
                recoverability=FailureRecoverability.NON_RECOVERABLE,
                severity=failure.severity,
            )

        # ───────── FALLBACK ─────────
        return FailureClass(
            domain=FailureDomain.UNKNOWN,
            nature=FailureNature.INVALID,
            recoverability=FailureRecoverability.NON_RECOVERABLE,
            severity=failure.severity,
        )
