from typing import List, Optional
from pydantic import BaseModel, Field

class CognitiveStateBase(BaseModel):
    """
    Base class for all cognitive objects in ArborMind.
    Enforces that reasoning is measured and grounded.
    """
    reasoning_depth_score: float = Field(
        ..., 
        description="A self-assessed score (0.0 to 1.0) of how deep and multi-layered the reasoning is.",
        ge=0.0, le=1.0
    )
    confidence_score: float = Field(
        ..., 
        description="A self-assessed confidence score (0.0 to 1.0) in the accuracy of the cognition.",
        ge=0.0, le=1.0
    )
    evidence_links: List[str] = Field(
        ..., 
        description="List of specific line numbers, logs, or file paths that justify the cognitive claims."
    )

class ReviewReportSchema(CognitiveStateBase):
    """
    Typed schema for Marcus's quality review observations.
    """
    strengths: List[str] = Field(
        ..., 
        description="Specific positive observations about the codebase or architecture."
    )
    weaknesses: List[str] = Field(
        ..., 
        description="Specific negative observations, flaws, or missing implementations."
    )
    missing_elements: List[str] = Field(
        default_factory=list, 
        description="Elements that were expected but are completely missing."
    )
    inconsistencies: List[str] = Field(
        default_factory=list, 
        description="Contradictions between different files or architectural layers."
    )
    risks: List[str] = Field(
        default_factory=list, 
        description="Future risks if the current architecture is maintained."
    )
    summary: str = Field(
        ..., 
        description="A brief, purely observational summary of the codebase state."
    )
