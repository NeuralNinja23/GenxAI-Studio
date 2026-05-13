# app/orchestration/review_report.py
"""
Immutable Review Report Schema.

INVARIANTS:
- No booleans (no pass/fail)
- No scores (no quality ratings)
- Observations only
- Never controls execution
"""

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class ReviewReport:
    """
    Immutable observation record from Marcus.
    
    This is EVIDENCE, not CONTROL.
    - ArborMind may use this to bias divergence
    - FAST ignores this entirely
    - Workflow Governor stores this but never gates on it
    """
    phase: str
    strengths: List[str]
    weaknesses: List[str]
    missing_elements: List[str]
    inconsistencies: List[str]
    risks: List[str]
    summary: str
    
    def to_evidence_string(self) -> str:
        """Convert to a string for passing as context to next phases."""
        parts = [f"## Review: {self.phase}"]
        
        if self.strengths:
            parts.append("### Strengths")
            parts.extend(f"- {s}" for s in self.strengths)
        
        if self.weaknesses:
            parts.append("### Weaknesses")
            parts.extend(f"- {w}" for w in self.weaknesses)
        
        if self.missing_elements:
            parts.append("### Missing Elements")
            parts.extend(f"- {m}" for m in self.missing_elements)
        
        if self.inconsistencies:
            parts.append("### Inconsistencies")
            parts.extend(f"- {i}" for i in self.inconsistencies)
        
        if self.risks:
            parts.append("### Risks")
            parts.extend(f"- {r}" for r in self.risks)
        
        if self.summary:
            parts.append(f"### Summary\n{self.summary}")
        
        return "\n".join(parts)


def empty_review(phase: str) -> ReviewReport:
    """Create an empty review (used when Marcus fails or is unavailable)."""
    return ReviewReport(
        phase=phase,
        strengths=[],
        weaknesses=[],
        missing_elements=[],
        inconsistencies=[],
        risks=[],
        summary="No review available."
    )
