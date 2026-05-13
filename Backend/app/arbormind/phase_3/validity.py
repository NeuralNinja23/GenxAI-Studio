from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from app.arbormind.adapters.oracle import OracleEvidence


# Tunable but explicit thresholds
MARCUS_MIN_SCORE = 0.6
VISUAL_MIN_SCORE = 0.7


@dataclass(frozen=True)
class ValidityResult:
    valid: bool
    reason: str
    violations: List[str]


class ValidityEvaluator:
    """
    Epistemic validity evaluator.

    This evaluator:
    - does NOT rank
    - does NOT repair
    - does NOT mutate
    - does NOT decide execution
    """

    def evaluate(
        self,
        branch_payload: Dict[str, Any],
        oracle: Optional[OracleEvidence],
    ) -> ValidityResult:

        violations: List[str] = []

        # ───────── STRUCTURAL SANITY (cheap, first) ─────────
        if "reasoning_trace" not in branch_payload:
            violations.append("missing_reasoning_trace")

        if "hypothesis" not in branch_payload:
            violations.append("missing_hypothesis")

        # If no oracle evidence, pass validity check (passthrough mode)
        if oracle is None:
            if violations:
                return ValidityResult(
                    valid=False,
                    reason="structural_invalid",
                    violations=violations,
                )
            return ValidityResult(
                valid=True,
                reason="branch_passthrough",
                violations=[],
            )

        # ───────── LOGIC WITNESS ─────────
        if not oracle.logic.valid:
            violations.append("logic_invalid")

        # ───────── MARCUS (EPISTEMIC QUALITY) ─────────
        if oracle.marcus.quality_score < MARCUS_MIN_SCORE:
            violations.append("epistemic_low_confidence")

        # ───────── VISUAL (OPTIONAL MODALITY) ─────────
        if oracle.visual is not None and oracle.visual.score is not None:
            if oracle.visual.score < VISUAL_MIN_SCORE:
                violations.append("visual_invalid")

        if violations:
            return ValidityResult(
                valid=False,
                reason="branch_ungrounded",
                violations=violations,
            )

        return ValidityResult(
            valid=True,
            reason="branch_grounded",
            violations=[],
        )

