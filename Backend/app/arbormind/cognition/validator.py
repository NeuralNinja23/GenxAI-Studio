from typing import Any
from .models import CognitiveStateBase

class EpistemicValidationError(Exception):
    """Raised when cognition fails epistemic validation."""
    pass

class CognitionValidator:
    """
    Validates typed cognitive states.
    Ensures that ArborMind does not accept fabricated or shallow insight.
    """
    
    @staticmethod
    def validate(state: CognitiveStateBase) -> bool:
        """
        Validates the cognitive state object.
        Returns True if valid, raises EpistemicValidationError if invalid.
        """
        if not isinstance(state, CognitiveStateBase):
            raise EpistemicValidationError("Input must be a Typed Cognitive State.")
            
        # 1. Check reasoning depth
        if state.reasoning_depth_score < 0.3:
            raise EpistemicValidationError(
                f"Shallow reasoning rejected (depth: {state.reasoning_depth_score}). "
                "Agent must provide multi-layered analysis."
            )
            
        # 2. Check confidence thresholds
        if state.confidence_score < 0.2:
            raise EpistemicValidationError(
                f"Low confidence cognition rejected (confidence: {state.confidence_score})."
            )
            
        # 3. Epistemic Validation (Evidence Grounding)
        if not state.evidence_links or len(state.evidence_links) == 0:
            raise EpistemicValidationError(
                "Cognition lacks epistemic grounding. "
                "You must provide specific evidence_links (e.g., line numbers, logs) to justify claims."
            )
            
        return True
