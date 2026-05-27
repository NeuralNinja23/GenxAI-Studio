# app/runtime/reality_sync.py
"""
V4 Reality Synchronization Engine — Stage 5: Runtime Synchronization

The authoritative reality bridge matching DB topology, filesystem projection,
and runtime execution leases. Enforces the Reality Authority Law: synchronization
layers may observe, classify, invalidate, and freeze execution states, but may
NEVER directly mutate canonical topology or filesystem projections.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import hashlib
from pydantic import BaseModel

from app.core.logging import log
from app.runtime.runtime_projection_validator import RuntimeProjectionValidator, ParityReport
from app.runtime.drift_detection import DriftSeverity, DriftResponse
from app.topology.topology_version_manager import TopologyVersionManager
from app.models.runtime_models import RuntimeTransaction, TransactionStatus
from app.runtime.leases import LeaseManager

class RealityDivergenceCollapse(Exception):
    """Raised when severe multi-layer divergence or broken lease requires immediate branch collapse."""


class RealitySyncResult(BaseModel):
    is_synchronized: bool
    system_hash: str
    topology_hash: str
    ast_hash: str
    filesystem_hash: str
    prev_tx_hash: str
    parity_report: Optional[Any] = None


class RealitySync:
    """
    Authoritative Reality Bridge.
    Observe, classify, invalidate, and freeze - NEVER directly mutate.
    """

    @classmethod
    async def synchronize_reality(cls, project_id: str, project_path: Path, active_lease_id: Optional[str] = None) -> RealitySyncResult:
        log("REALITY_SYNC", f"🌉 Initiating reality synchronization bridge check for {project_id}")

        # ── 1. Continuous parity scanning ──────────────────────
        parity: ParityReport = await RuntimeProjectionValidator.validate_parity(project_id, project_path)

        # ── 2. Active lease checks ────────────────────────────
        lease_valid = True
        if active_lease_id:
            # Enforce lease authority via LeaseManager
            lm = LeaseManager()
            # If the lease is expired or stolen, this is a split-brain condition
            active_lease = await lm.get_active_lease(project_id)
            has_matching_active = active_lease is not None and active_lease.lease_id == active_lease_id
            if not has_matching_active:
                log("REALITY_SYNC", f"❌ Active lease validation failed: lease {active_lease_id[:8]} expired or stolen!")
                lease_valid = False

        # ── 3. Divergence Collapse triggers ─────────────────────
        divergence_detected = not parity.topology_hash_aligned or parity.severity in [DriftSeverity.SEVERE, DriftSeverity.CRITICAL] or not lease_valid
        
        if divergence_detected:
            log("REALITY_SYNC", "🚨 SEVERE/CRITICAL divergence detected! Raising RealityDivergenceCollapse to initiate Branch Invalidation.")
            # Freeze/invalidate branch execution
            await cls._invalidate_branch_state(project_id)
            raise RealityDivergenceCollapse(
                f"Multi-layer divergence collapse in {project_id}: "
                f"congruence={parity.congruence_score:.2f}, "
                f"severity={parity.severity.value}, "
                f"lease_valid={lease_valid}"
            )

        # ── 4. Retrieve canonical topology, AST, and prev TX hashes ──
        db_graph = await TopologyVersionManager.get_active_topology(project_id)
        topology_hash = db_graph.graph_hash if db_graph else "EMPTY_TOPOLOGY_HASH"

        ast_manifest_path = project_path / ".genx_ast_manifest.json"
        ast_hash = "EMPTY_AST_HASH"
        if ast_manifest_path.exists():
            try:
                import json
                with open(ast_manifest_path, "r", encoding="utf-8") as f:
                    manifest_data = json.load(f)
                projections = manifest_data.get("projections", {})
                # AST projection hash is the hash of the projection path mapping
                ast_json = json.dumps(projections, sort_keys=True)
                ast_hash = hashlib.sha256(ast_json.encode()).hexdigest()
            except Exception as err:
                log("REALITY_SYNC", f"⚠️ Error computing AST hash: {err}")

        # Compute physical filesystem hash representing current baseline file states
        from app.runtime.drift_detection import DriftDetector
        drift_detector = DriftDetector(project_path)
        filesystem_hash = drift_detector.compute_current_filesystem_hash()

        # Query the database to retrieve the latest committed transaction's cryptographic hash
        latest_committed_tx = await RuntimeTransaction.find(
            {"project_id": project_id, "status": TransactionStatus.COMMITTED}
        ).sort("-committed_at").to_list(1)
        
        prev_tx_hash = "GENESIS_TX_HASH"
        if latest_committed_tx:
            prev_tx_hash = latest_committed_tx[0].tx_hash or "GENESIS_TX_HASH"

        # ── 5. Form the Cryptographic Structural Integrity Chained Hash ──
        system_input = f"{topology_hash}||{ast_hash}||{filesystem_hash}||{prev_tx_hash}"
        system_hash = hashlib.sha256(system_input.encode()).hexdigest()

        log("REALITY_SYNC", f"🔐 Chained System Integrity Hash: {system_hash[:16]}... (prev={prev_tx_hash[:8]})")

        return RealitySyncResult(
            is_synchronized=True,
            system_hash=system_hash,
            topology_hash=topology_hash,
            ast_hash=ast_hash,
            filesystem_hash=filesystem_hash,
            prev_tx_hash=prev_tx_hash,
            parity_report=parity
        )

    @classmethod
    async def _invalidate_branch_state(cls, project_id: str) -> None:
        """
        Freeze branch state execution, revoke leases, block new transactions,
        and mark active sessions as paused/invalidated.
        NO MUTATIONS of actual codebase filesystem or topology graphs are made here.
        """
        log("REALITY_SYNC", f"❄️ Freezing execution states and invalidating active branches for {project_id}")
        
        try:
            # 1. Revoke active execution leases
            from app.models.runtime_models import ExecutionLease, LeaseStatus
            from app.core.time import utc_now
            active_leases = await ExecutionLease.find(
                {"project_id": project_id, "status": LeaseStatus.ACTIVE}
            ).to_list()
            for lease in active_leases:
                lease.status = LeaseStatus.RELEASED
                lease.released_at = utc_now()
                await lease.save()
                log("REALITY_SYNC", f"   🔒 Revoked active lease: {lease.lease_id[:8]}")

            # 2. Pause/Invalidate WorkflowSession
            from app.models.workflow import WorkflowSession
            session = await WorkflowSession.find_one({"project_id": project_id})
            if session:
                session.is_running = False
                session.is_paused = True
                await session.save()
                log("REALITY_SYNC", "   ⏸️ Paused active workflow session execution context.")
        
        except Exception as err:
            log("REALITY_SYNC", f"⚠️ Error invalidating active branch state: {err}")
