# oracle.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional

# External witnesses
from app.validation.syntax_validator import validate_syntax


# ─────────────────────────────────────────────────────────────
# Evidence Models (Pure Observation)
# ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class LogicEvidence:
    valid: bool
    errors: list[str]


@dataclass(frozen=True)
class MarcusEvidence:
    quality_score: float
    concerns: list[str]


@dataclass(frozen=True)
class VisualEvidence:
    issues: list[str]
    score: Optional[float]


@dataclass(frozen=True)
class OracleEvidence:
    """
    Aggregated, non-authoritative observations.
    """
    logic: LogicEvidence
    marcus: MarcusEvidence
    visual: Optional[VisualEvidence]
    metadata: Dict[str, Any]


# ─────────────────────────────────────────────────────────────
# Oracle (Witness, Not Judge)
# ─────────────────────────────────────────────────────────────

class Oracle:
    """
    Multimodal witness.

    This class:
    - observes
    - reports
    - never decides
    """

    def __init__(self, project_path: str = ""):
        self._project_path = project_path

    def observe(
        self,
        *,
        code: Optional[str] = None,
        reasoning_trace: Optional[str] = None,
        visual_input: Optional[Any] = None,
        file_path: str = "unknown.py",
    ) -> OracleEvidence:
        """
        Collect observations from all available witnesses.
        """

        # ───────── LOGIC WITNESS ─────────
        if code is not None:
            logic_result = validate_syntax(path=file_path, content=code)
            logic = LogicEvidence(
                valid=logic_result.valid,
                errors=logic_result.errors,
            )
        else:
            logic = LogicEvidence(valid=True, errors=[])

        # ───────── MARCUS WITNESS ─────────
        # Placeholder - MarcusSupervisor.review() may not exist yet
        marcus = MarcusEvidence(
            quality_score=1.0,
            concerns=[],
        )


        # ───────── VISUAL WITNESS (OPTIONAL) ─────────
        visual = None
        if visual_input is not None:
            # Placeholder for future visual analyzers
            visual = VisualEvidence(
                issues=[],
                score=None,
            )

        return OracleEvidence(
            logic=logic,
            marcus=marcus,
            visual=visual,
            metadata={
                "sources": ["logic", "marcus"] + (["visual"] if visual else [])
            },
        )
