# app/runtime/execution_kernel.py
"""
V4 Execution Kernel — Stage 1: Freeze Runtime

The Immutable Runtime OS Core.

The execution kernel is the SOLE orchestrator of:
    - Execution lease acquisition and release
    - Substrate integrity verification
    - Drift detection and response
    - Pre-cycle contract enforcement
    - Projection snapshot creation
    - Transaction lifecycle (begin → oracle check → commit / rollback)
    - Filesystem restoration on rollback

Separation of concerns (from implementation plan):
    ┌───────────────────────────────────────────────────────┐
    │  COGNITIVE LAYER  (Proposes — Non-Authoritative)       │
    │  sentinel_core, branch, mutation_engine, faculties        │
    └───────────────┬───────────────────────────────────────┘
                    │  Bounded Mutation Proposal (PatchIR)
                    ▼
    ┌───────────────────────────────────────────────────────┐
    │  EXECUTION KERNEL  (Decides — Authoritative)           │
    │  1. verify_pre_cycle_contracts()                       │
    │  2. acquire_lease()                                    │
    │  3. create_snapshot()                                  │
    │  4. detect_drift() → respond                           │
    │  5. begin_transaction()                                │
    │  6. [AST Projector writes files]  (Stage 3+)          │
    │  7. [Oracle pipeline runs]         (Stage 4+)          │
    │  8. commit() or rollback()                             │
    │  9. release_lease()                                    │
    └───────────────────────────────────────────────────────┘

Immutability guarantee:
    This file is in the Immutable Runtime Kernel set.
    No cognitive faculty, no LLM output, and no configuration
    mutation may alter the behavior of this kernel.

Stage 1 status:
    The kernel is fully operational for:
        - Lease management
        - Substrate locking / verification
        - Snapshot creation and restoration
        - Transaction lifecycle
        - Drift detection and rollback

    Awaiting Stage 3 wiring:
        - AST Projector integration (replace _stub_ast_projection)

    Awaiting Stage 4 wiring:
        - Oracle pipeline integration (replace _stub_oracle_pipeline)
"""

import asyncio
import uuid
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.time import utc_now

from app.core.logging import log
from app.models.runtime_models import MutationTier, RuntimeTransaction, TransactionStatus
from app.sentinel.runtime.drift_detection import DriftDetector, DriftResponse, DriftSeverity
from app.sentinel.runtime.execution_contracts import ExecutionContracts
from app.sentinel.runtime.leases import (
    DEFAULT_LEASE_TTL_SECONDS,
    LeaseAcquisitionError,
    LeaseManager,
)
from app.sentinel.runtime.projection_snapshots import SnapshotManager
from app.sentinel.runtime.transaction_engine import TransactionEngine
from app.substrate.substrate_manager import SubstrateManager
from app.sentinel.failure_memory.failure_recorder import record_failure, FailureType, Severity


# ─────────────────────────────────────────────────────────────
# Kernel-level errors
# ─────────────────────────────────────────────────────────────

class KernelContractViolation(Exception):
    """Raised when pre-cycle contracts fail — cycle does not begin."""


class KernelDriftViolation(Exception):
    """Raised when CRITICAL drift requires immediate rollback before cycle."""


class KernelLeaseError(Exception):
    """Raised when lease cannot be acquired."""


class KernelRollbackError(Exception):
    """Raised when rollback itself fails — requires manual intervention."""


# ─────────────────────────────────────────────────────────────
# Projection Cycle Context
# ─────────────────────────────────────────────────────────────

class ProjectionCycleContext:
    """
    Carries all state for a single projection cycle.
    Passed between kernel stages to avoid global state.
    """

    def __init__(
        self,
        project_id: str,
        project_path: Path,
        mutation_tier: MutationTier,
        proposed_writes: List[str],
        required_oracle_tiers: Optional[List[str]] = None,
    ):
        self.cycle_id: str = str(uuid.uuid4())
        self.project_id = project_id
        self.project_path = project_path
        self.mutation_tier = mutation_tier
        self.proposed_writes = proposed_writes
        self.required_oracle_tiers = required_oracle_tiers or []

        # Populated during the cycle
        self.lease = None
        self.snapshot = None
        self.transaction: Optional[RuntimeTransaction] = None
        self.oracle_results: Dict[str, Any] = {}
        self.oracle_evidence_keys: List[str] = []
        self.files_written: List[str] = []
        self.files_deleted: List[str] = []

        self.started_at = utc_now()
        self.succeeded: Optional[bool] = None


# ─────────────────────────────────────────────────────────────
# Execution Kernel
# ─────────────────────────────────────────────────────────────

class ExecutionKernel:
    """
    The Immutable Runtime OS Core.

    One kernel instance is created per backend process.
    Multiple projection cycles may run sequentially (never concurrently —
    the lease system enforces this at the project level).

    Usage (Stage 1+):
        kernel = ExecutionKernel()
        async with kernel.projection_cycle(ctx) as cycle:
            # Stage 3+: AST Projector writes files here
            # Stage 4+: Oracle pipeline runs here
            # Commit/rollback is automatic on context exit

    For Stage 1 (wiring the workflow engine):
        result = await kernel.run_scaffold_cycle(project_id, project_path)
    """

    def __init__(self, kernel_id: Optional[str] = None):
        self._kernel_id: str = kernel_id or str(uuid.uuid4())
        self._lease_manager = LeaseManager(kernel_id=self._kernel_id)
        log("KERNEL", f"🚀 ExecutionKernel initialized (id={self._kernel_id[:8]}...)")

    # ──────────────────────────────────────────────────────────
    # Full projection cycle (Stage 3+ integration point)
    # ──────────────────────────────────────────────────────────

    async def run_projection_cycle(
        self,
        ctx: ProjectionCycleContext,
        ast_projection_fn=None,
        oracle_pipeline_fn=None,
    ) -> bool:
        """
        Execute a complete, transactional projection cycle.

        Stage 1 wiring:
            ast_projection_fn:  Stub (writes no files). Replaced in Stage 3.
            oracle_pipeline_fn: Stub (returns all-pass). Replaced in Stage 4.

        Returns:
            True if the cycle committed successfully, False if rolled back.
        """
        log("KERNEL", f"⚡ Projection cycle START: {ctx.cycle_id} "
                      f"(project={ctx.project_id}, tier={ctx.mutation_tier.name})")

        try:
            # ── 1. Contract verification ──────────────────────
            contract_result = await ExecutionContracts.verify_pre_cycle(
                project_id=ctx.project_id,
                project_path=ctx.project_path,
                mutation_tier=ctx.mutation_tier,
                proposed_writes=ctx.proposed_writes,
                required_oracle_tiers=ctx.required_oracle_tiers,
            )
            if not contract_result.passed:
                violations = [v.rule for v in contract_result.violations]
                raise KernelContractViolation(
                    f"Pre-cycle contracts failed: {violations}"
                )

            # ── 2. Acquire lease ──────────────────────────────
            try:
                ctx.lease = await self._lease_manager.acquire(
                    project_id=ctx.project_id,
                    cycle_id=ctx.cycle_id,
                )
            except LeaseAcquisitionError as e:
                raise KernelLeaseError(str(e))

            # ── 3. Create snapshot ────────────────────────────
            snapshot_mgr = SnapshotManager(ctx.project_path)
            ctx.snapshot = await snapshot_mgr.create_snapshot(
                project_id=ctx.project_id,
                cycle_id=ctx.cycle_id,
            )

            # ── 4. Drift detection ────────────────────────────
            drift_detector = DriftDetector(ctx.project_path)
            drift_report = await drift_detector.detect(
                project_id=ctx.project_id,
                baseline_snapshot_id=ctx.snapshot.snapshot_id,
            )

            if drift_report.recommended_response == DriftResponse.ROLLBACK:
                log("KERNEL", f"⛔ CRITICAL drift detected — initiating rollback before cycle")
                await self._perform_rollback(ctx, "Critical drift detected before cycle start")
                raise KernelDriftViolation(
                    f"Critical drift in {ctx.project_id}: "
                    f"{drift_report.substrate_violations}"
                )

            if drift_report.recommended_response == DriftResponse.RECONSTRUCT:
                log("KERNEL", f"⚠️ Severe drift detected — initiating forensic topology reconstruction")
                from app.sentinel.runtime.reconstruction import ForensicReconstruction
                await ForensicReconstruction.reconstruct_topology(ctx.project_id, ctx.project_path)

            # ── 5. Begin transaction ──────────────────────────
            ctx.transaction = await TransactionEngine.begin(
                project_id=ctx.project_id,
                lease_id=ctx.lease.lease_id,
                mutation_tier=ctx.mutation_tier,
                snapshot_id=ctx.snapshot.snapshot_id,
            )

            # ── 6. AST Projection (Stage 3 wiring point) ──────
            ast_fn = ast_projection_fn or _stub_ast_projection
            projection_result = await ast_fn(ctx)
            ctx.files_written = projection_result.get("files_written", [])
            ctx.files_deleted = projection_result.get("files_deleted", [])

            await TransactionEngine.record_writes(
                ctx.transaction,
                files_written=ctx.files_written,
                files_deleted=ctx.files_deleted,
                pre_filesystem_hash=drift_detector.compute_current_filesystem_hash(),
            )

            # ── 7. Verify lease still held ────────────────────
            if not await self._lease_manager.verify_ownership(ctx.lease):
                raise KernelLeaseError("Lease lost during projection — rolling back")

            # ── 8. Oracle pipeline (Stage 4 wiring point) ─────
            oracle_fn = oracle_pipeline_fn or _stub_oracle_pipeline
            oracle_result = await oracle_fn(ctx)
            ctx.oracle_results = oracle_result.get("results", {})
            ctx.oracle_evidence_keys = oracle_result.get("evidence_keys", [])

            # ── 9. Commit or rollback ─────────────────────────
            post_fs_hash = drift_detector.compute_current_filesystem_hash()
            try:
                # Run continuous reality sync and compute structural integrity hashes
                from app.sentinel.runtime.reality_sync import RealitySync
                sync_res = await RealitySync.synchronize_reality(ctx.project_id, ctx.project_path, active_lease_id=ctx.lease.lease_id)
                
                # Fetch post-cycle hashes for commit
                from app.sentinel.topology.topology_version_manager import TopologyVersionManager
                db_graph = await TopologyVersionManager.get_active_topology(ctx.project_id)
                post_topo_hash = db_graph.graph_hash if db_graph else "EMPTY_TOPOLOGY_HASH"
                post_ast_hash = sync_res.ast_hash

                await TransactionEngine.commit(
                    tx=ctx.transaction,
                    oracle_results=ctx.oracle_results,
                    oracle_evidence_keys=ctx.oracle_evidence_keys,
                    post_topology_hash=post_topo_hash,
                    post_ast_hash=post_ast_hash,
                    post_filesystem_hash=post_fs_hash,
                )
                ctx.succeeded = True
                log("KERNEL", f"✅ Projection cycle {ctx.cycle_id} COMMITTED (system_hash={sync_res.system_hash[:12]}...)")

            except Exception as commit_err:
                log("KERNEL", f"❌ Commit failed: {commit_err}")
                await self._perform_rollback(ctx, str(commit_err))
                ctx.succeeded = False

        except (KernelContractViolation, KernelLeaseError, KernelDriftViolation):
            raise  # Re-raise to caller without rollback (cycle never started)

        except Exception as e:
            log("KERNEL", f"❌ Unexpected kernel error in cycle {ctx.cycle_id}: {e}")
            if ctx.transaction:
                await self._perform_rollback(ctx, f"Unexpected error: {e}")
            ctx.succeeded = False

        finally:
            # ── 10. Release lease ─────────────────────────────
            if ctx.lease:
                try:
                    await self._lease_manager.release(ctx.lease)
                except Exception as lease_err:
                    log("KERNEL", f"⚠️ Lease release error (non-fatal): {lease_err}")

        return ctx.succeeded is True

    # ──────────────────────────────────────────────────────────
    # Scaffold cycle (Stage 1 — workspace creation)
    # ──────────────────────────────────────────────────────────

    async def lock_substrate_after_scaffold(
        self,
        project_id: str,
        project_path: Path,
    ) -> None:
        """
        Lock the stable substrate after workspace scaffolding.

        Called by workflow/engine.py after template copy completes.
        This is the ONLY time SubstrateManifest is written.
        """
        await SubstrateManager.lock_substrate(
            project_id=project_id,
            project_path=project_path,
        )
        log("KERNEL", f"🔒 Substrate locked for {project_id}")

    # ──────────────────────────────────────────────────────────
    # Emergency rollback
    # ──────────────────────────────────────────────────────────

    async def emergency_rollback(
        self,
        project_id: str,
        project_path: Path,
        reason: str,
    ) -> bool:
        """
        Perform an emergency rollback to the most recent snapshot.
        Called when a critical error is detected outside a normal cycle.

        Returns True if successful, False if no snapshot available.
        """
        log("KERNEL", f"🆘 Emergency rollback initiated for {project_id}: {reason}")

        snapshot_mgr = SnapshotManager(project_path)
        snapshot = await SnapshotManager.get_latest_snapshot(project_id)

        if snapshot is None:
            log("KERNEL", f"⚠️ No snapshot available for emergency rollback of {project_id}")
            return False

        success = await snapshot_mgr.restore_snapshot(snapshot)
        if success:
            log("KERNEL", f"✅ Emergency rollback complete for {project_id}")
        else:
            log("KERNEL", f"❌ Emergency rollback FAILED for {project_id}")
        return success

    # ──────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────

    async def _perform_rollback(self, ctx: ProjectionCycleContext, reason: str) -> None:
        """Internal: roll back transaction and restore snapshot."""
        # Mark transaction as rolled back
        if ctx.transaction:
            await TransactionEngine.rollback(ctx.transaction, reason)

        # Restore snapshot
        if ctx.snapshot and ctx.project_path:
            snapshot_mgr = SnapshotManager(ctx.project_path)
            await snapshot_mgr.restore_snapshot(ctx.snapshot)
            log("KERNEL", f"↩️ Snapshot {ctx.snapshot.snapshot_id} restored for {ctx.project_id}")

        # ── Phase 6A: Record rollback to failure memory ─────────────────────
        record_failure(
            FailureType.KERNEL_ROLLBACK,
            Severity.CRITICAL,
            reason,
            project_id=ctx.project_id,
            branch_id=ctx.cycle_id,
            component="execution_kernel",
            node_type="KERNEL",
        )


# ─────────────────────────────────────────────────────────────
# Stage 1 stubs (replaced in later stages)
# ─────────────────────────────────────────────────────────────

async def _stub_ast_projection(ctx: ProjectionCycleContext) -> Dict[str, Any]:
    """
    Stage 3 wiring point — AST Projector.
    """
    from app.sentinel.topology.ast_projector import ASTProjector
    return await ASTProjector.project(ctx)


async def _stub_oracle_pipeline(ctx: ProjectionCycleContext) -> Dict[str, Any]:
    """
    Stage 4 wiring point — Oracle Pipeline.
    """
    from app.sentinel.oracles.pipeline import OraclePipeline
    return await OraclePipeline.run(ctx)


# ─────────────────────────────────────────────────────────────
# Singleton kernel instance
# ─────────────────────────────────────────────────────────────

_KERNEL_INSTANCE: Optional[ExecutionKernel] = None


def get_kernel() -> ExecutionKernel:
    """Get the singleton ExecutionKernel instance."""
    global _KERNEL_INSTANCE
    if _KERNEL_INSTANCE is None:
        _KERNEL_INSTANCE = ExecutionKernel()
    return _KERNEL_INSTANCE
