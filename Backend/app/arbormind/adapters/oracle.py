# oracle.py

from __future__ import annotations
from typing import Any, Dict, Optional

from app.arbormind.adapters.oracles.models import OracleEvidence
from app.arbormind.adapters.oracles.oracles import (
    StructuralOracle,
    RuntimeOracle,
    BrowserOracle,
    VisualOracle,
    SemanticOracle
)

class OracleSupervisor:
    """
    Multimodal Oracle Supervisor.
    Aggregates typed evidence from sub-oracles and computes the unified TotalLoss.
    """

    def __init__(self, project_path: str = ""):
        self._project_path = project_path
        
        self.structural = StructuralOracle()
        self.runtime = RuntimeOracle()
        self.browser = BrowserOracle()
        self.visual = VisualOracle()
        self.semantic = SemanticOracle()

    def observe(
        self,
        *,
        code: Optional[str] = None,
        file_path: str = "unknown.py",
        container_health: Optional[Dict[str, Any]] = None,
        browser_logs: Optional[list[str]] = None,
        screenshot_path: Optional[str] = None,
        dom_snapshot: Optional[str] = None,
        semantic_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Collect observations from all sub-oracles and compute TotalLoss.
        """
        
        evidences: Dict[str, OracleEvidence] = {}
        
        # 1. Structural Layer
        evidences["structural"] = self.structural.observe(code or "", file_path)
        
        # 2. Runtime Layer
        evidences["runtime"] = self.runtime.observe(container_health or {})
        
        # 3. Browser Layer
        evidences["browser"] = self.browser.observe(browser_logs or [])
        
        # 4. Visual Layer
        evidences["visual"] = self.visual.observe(screenshot_path or "", dom_snapshot or "")
        
        # 5. Semantic Layer
        evidences["semantic"] = self.semantic.observe(semantic_context or {})
        
        # ───────── UNIFIED LOSS MATHEMATICS ─────────
        # Weighted loss = loss_score * confidence
        
        w_struct = evidences["structural"].loss_score * evidences["structural"].confidence
        w_runtime = evidences["runtime"].loss_score * evidences["runtime"].confidence
        w_browser = evidences["browser"].loss_score * evidences["browser"].confidence
        w_visual = evidences["visual"].loss_score * evidences["visual"].confidence
        w_semantic = evidences["semantic"].loss_score * evidences["semantic"].confidence
        
        # TotalLoss = (0.2*structural) + (0.2*runtime) + (0.2*browser) + (0.2*visual) + (0.2*semantic)
        total_loss = (0.2 * w_struct) + (0.2 * w_runtime) + (0.2 * w_browser) + (0.2 * w_visual) + (0.2 * w_semantic)
        
        # Aggregate semantic signatures for FailureMemory topology
        primary_signature = "healthy"
        for key, ev in evidences.items():
            if not ev.passed and ev.semantic_signature:
                primary_signature = ev.semantic_signature
                break
                
        return {
            "total_loss": total_loss,
            "primary_signature": primary_signature,
            "passed": total_loss == 0.0,
            "evidences": evidences
        }
