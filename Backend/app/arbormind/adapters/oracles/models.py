from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum

class FrontendFailure(str, Enum):
    MISSING_DEPENDENCY = "MissingDependency"
    RUNTIME_CRASH = "RuntimeCrash"
    HYDRATION_FAILURE = "HydrationFailure"
    NETWORK_FAILURE = "NetworkFailure"
    BLANK_SCREEN = "BlankScreen"
    INFINITE_RENDER = "InfiniteRender"
    CSS_PARSER_FAILURE = "CSSParserFailure"
    VISUAL_REGRESSION = "VisualRegression"
    BEHAVIORAL_FAILURE = "BehavioralFailure"
    SEMANTIC_FAILURE = "SemanticFailure"

class OracleEvidence(BaseModel):
    """
    Typed execution evidence.
    Replaces binary pass/fail flags with rich, classifiable failure state.
    """
    oracle_type: str = Field(..., description="E.g., BrowserOracle, VisualOracle, SemanticOracle")
    passed: bool
    severity: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in the oracle's assessment")
    
    failure_class: Optional[FrontendFailure] = None
    
    # Semantic clustering key (e.g., 'frontend_dependency_resolution_failure')
    semantic_signature: str = Field(..., description="High-level semantic categorization for clustering and memory reuse")

    console_errors: List[str] = Field(default_factory=list)
    runtime_exceptions: List[str] = Field(default_factory=list)
    failed_requests: List[str] = Field(default_factory=list)

    screenshot_path: Optional[str] = None
    dom_snapshot: Optional[str] = None

    stacktrace: Optional[str] = None
    visible_blank_screen: bool = False
    
    # Pre-calculated local loss for this specific oracle
    loss_score: float = Field(..., ge=0.0, le=1.0)
