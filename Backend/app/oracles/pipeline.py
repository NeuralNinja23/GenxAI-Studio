# app/oracles/pipeline.py
"""
V4 Oracle Pipeline Orchestrator — Stage 4: Oracle Layer

Sequentially executes the validation physics stack (HARD first, then SOFT)
and registers the epistemic traces in the EvidenceRegistry ledger.
"""

from typing import Dict, List, Any
from pathlib import Path

from app.core.logging import log
from app.oracles.syntax_oracle import SyntaxOracle
from app.oracles.topology_oracle import TopologyOracle
from app.oracles.behavioral_oracle import BehavioralOracle
from app.oracles.runtime_oracle import RuntimeOracle
from app.oracles.visual_oracle import VisualOracle
from app.oracles.semantic_oracle import SemanticOracle
from app.oracles.convergence_oracle import ConvergenceOracle
from app.governance.evidence_registry import EvidenceRegistry

class OraclePipeline:
    """
    Verification Physics Pipeline.
    Strictly segregates HARD and SOFT oracles.
    Registers physical evidence traces for validation groundedness.
    """

    @classmethod
    async def run(cls, cycle_ctx: Any) -> Dict[str, Any]:
        """
        Execute the entire verified pipeline on the current cycle context.
        Raises ValueError if any HARD oracle fails.
        """
        project_id = cycle_ctx.project_id
        project_path = Path(cycle_ctx.project_path)

        log("ORACLE_PIPELINE", f"⚡ Initiating multi-layer validation pipeline for {project_id}")

        # Instantiate verification stack
        hard_oracles = [
            SyntaxOracle(),
            TopologyOracle(),
            BehavioralOracle(),
            RuntimeOracle()
        ]

        soft_oracles = [
            VisualOracle(),
            SemanticOracle(),
            ConvergenceOracle()
        ]

        results = {}
        evidence_keys = []

        # ── 1. HARD validation loop ───────────────────────────
        for oracle in hard_oracles:
            res = await oracle.validate(project_id, project_path, cycle_ctx)
            results[oracle.name] = res.dict()
            
            # Persist trace in the EvidenceRegistry ledger
            ev_key = await EvidenceRegistry.register_evidence(
                project_id=project_id,
                claim_type=oracle.name,
                evidence_payload={"reason": res.reason, "metrics": res.metrics},
                custom_key=res.evidence_key
            )
            evidence_keys.append(ev_key)

            if not res.passed:
                log("ORACLE_PIPELINE", f"❌ HARD Oracle '{oracle.name}' FAILED: {res.reason}. Halting commit.")
                # Immediately raise error to abort transaction commit and trigger rollback
                raise ValueError(f"HARD Oracle {oracle.name} failed: {res.reason}")

            log("ORACLE_PIPELINE", f"✅ HARD Oracle '{oracle.name}' passed. Evidence locked: {ev_key[:12]}...")

        # ── 2. SOFT advisory loop ────────────────────────────
        for oracle in soft_oracles:
            res = await oracle.validate(project_id, project_path, cycle_ctx)
            results[oracle.name] = res.dict()
            
            ev_key = await EvidenceRegistry.register_evidence(
                project_id=project_id,
                claim_type=oracle.name,
                evidence_payload={"reason": res.reason, "metrics": res.metrics},
                custom_key=res.evidence_key
            )
            evidence_keys.append(ev_key)
            log("ORACLE_PIPELINE", f"ℹ️ SOFT Oracle '{oracle.name}' completed. Evidence locked: {ev_key[:12]}...")

        return {
            "results": results,
            "evidence_keys": evidence_keys
        }
