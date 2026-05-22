from typing import Optional, Dict, Any
from .models import OracleEvidence, FrontendFailure

class StructuralOracle:
    """Evaluates AST validity, imports, and core syntax."""
    
    def observe(self, code: str, file_path: str) -> OracleEvidence:
        # Placeholder for real AST parsing
        return OracleEvidence(
            oracle_type="StructuralOracle",
            passed=True,
            severity=0.0,
            confidence=0.9,
            semantic_signature="syntax_valid",
            loss_score=0.0
        )

class RuntimeOracle:
    """Evaluates container/process/runtime health."""
    
    def observe(self, container_health: Dict[str, Any]) -> OracleEvidence:
        # Placeholder for real health check
        return OracleEvidence(
            oracle_type="RuntimeOracle",
            passed=True,
            severity=0.0,
            confidence=0.95,
            semantic_signature="runtime_healthy",
            loss_score=0.0
        )

class BrowserOracle:
    """Captures console errors, hydration crashes, and network failures via Playwright."""
    
    def observe(self, browser_logs: list[str]) -> OracleEvidence:
        # Example of detecting a Vite missing import
        for log in browser_logs:
            if "Failed to resolve import" in log:
                return OracleEvidence(
                    oracle_type="BrowserOracle",
                    passed=False,
                    severity=0.8,
                    confidence=0.9,
                    failure_class=FrontendFailure.MISSING_DEPENDENCY,
                    semantic_signature="frontend_dependency_resolution_failure",
                    console_errors=[log],
                    loss_score=0.8
                )
                
        return OracleEvidence(
            oracle_type="BrowserOracle",
            passed=True,
            severity=0.0,
            confidence=0.8,
            semantic_signature="browser_execution_clean",
            loss_score=0.0
        )

class VisualOracle:
    """Checks for blank screens, layout collapse, and rendering anomalies."""
    
    def observe(self, screenshot_path: str, dom_snapshot: str) -> OracleEvidence:
        # Placeholder for real visual VLM evaluation
        return OracleEvidence(
            oracle_type="VisualOracle",
            passed=True,
            severity=0.0,
            confidence=0.6,  # Lower confidence since it's a stub/heuristic
            semantic_signature="visual_render_successful",
            screenshot_path=screenshot_path,
            dom_snapshot=dom_snapshot,
            loss_score=0.0
        )

class SemanticOracle:
    """
    FUTURE LAYER: Evaluates pure business logic correctness.
    Example: CRM permissions, workflow states, approval chains.
    """
    
    def observe(self, semantic_context: Dict[str, Any]) -> OracleEvidence:
        return OracleEvidence(
            oracle_type="SemanticOracle",
            passed=True,
            severity=0.0,
            confidence=0.5,
            semantic_signature="business_logic_unverified",
            loss_score=0.0
        )
