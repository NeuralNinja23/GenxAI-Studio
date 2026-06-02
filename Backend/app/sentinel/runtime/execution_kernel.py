"""
V4 Execution Kernel — Stage 3: Atomic Transactional Pipeline
The Immutable Runtime OS Core.
"""

import asyncio
import uuid
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.logging import log
from app.models.runtime_models import MutationTier
from app.sentinel.runtime.leases import LeaseAcquisitionError, LeaseManager
from app.sentinel.runtime.projection_snapshots import SnapshotManager
from app.sentinel.runtime.transaction_engine import TransactionEngine
from app.substrate.substrate_manager import SubstrateManager
from app.sentinel.verification.verification_gate import SentinelVerificationGate
from app.sentinel.topology.project_graph import ProjectTopologyGraph
from app.sentinel.validation.validation_recorder import ValidationRecorder
from app.sentinel.failure_memory.failure_analyzer import FailureAnalyzer # Verified import path
from app.sentinel.topology.ast_projector import ASTProjector # Verified import path
import time
from app.sentinel.validation.validation_bus import ValidationBus
from app.sentinel.validation.validation_recorder import ValidationRecorder
from app.sentinel.validation.validation_logger import ValidationLogger

# ─────────────────────────────────────────────────────────────
# 1. Context (Defined FIRST)
# ─────────────────────────────────────────────────────────────
class ProjectionCycleContext:
    def __init__(
        self, 
        project_id: str, 
        project_path: Path, 
        mutation_tier: MutationTier, 
        proposed_writes: List[str],
        required_oracle_tiers: Optional[List[str]] = None
    ):
        self.cycle_id = str(uuid.uuid4())
        self.project_id = project_id
        self.project_path = project_path
        self.mutation_tier = mutation_tier
        self.proposed_writes = proposed_writes
        self.required_oracle_tiers = required_oracle_tiers or []
        self.lease = None
        self.snapshot = None
        self.transaction = None
        self.files_written = []
        self.succeeded = None

class LLMClientWrapper:
    async def generate(self, system_prompt: str, user_message: str) -> str:
        from app.llm.adapter import call_llm
        return await call_llm(prompt=user_message, system_prompt=system_prompt)

# ─────────────────────────────────────────────────────────────
# 2. Execution Kernel (Defined SECOND)
# ─────────────────────────────────────────────────────────────
class ExecutionKernel:
    def __init__(self):
        self._kernel_id = str(uuid.uuid4())
        self._lease_manager = LeaseManager(kernel_id=self._kernel_id)
        self.llm_client = LLMClientWrapper()
        log("KERNEL", f"🚀 ExecutionKernel initialized (id={self._kernel_id[:8]}...)")

    async def run_projection_cycle(self, ctx: ProjectionCycleContext, graph: Any, llm_client: Any) -> Dict[str, Any]:
        """Executes the Sentinel atomic control law."""
        log("KERNEL", f"⚡ Projection cycle START: {ctx.cycle_id}")
        
        start_time = time.time()
        ValidationRecorder.record_system_event("cycle_started", "INFO", f"Starting projection cycle {ctx.cycle_id}")
        
        try:
            ctx.lease = await self._lease_manager.acquire(ctx.project_id, ctx.cycle_id)
            snapshot_mgr = SnapshotManager(ctx.project_path)
            ctx.snapshot = await snapshot_mgr.create_snapshot(ctx.project_id, ctx.cycle_id)

            ctx.transaction = await TransactionEngine.begin(
                ctx.project_id, ctx.lease.lease_id, ctx.mutation_tier, ctx.snapshot.snapshot_id
            )

            # Stage 3: Project
            projector = ASTProjector(llm_client=llm_client)
            projection_result = await projector.project(ctx, graph)
            ctx.files_written = projection_result.get("files_written", [])

            # Stage 4: Gate
            staging_path = ctx.project_path / ".genx_staging"
            verification = SentinelVerificationGate.verify(staging_path, graph)
            ctx.verification = verification

            if verification.recommendation == "REJECT":
                reason = f"Oracle REJECT: {verification.failure_classification}"
                ctx._telemetry_failure_type = verification.failure_classification
                ctx._telemetry_termination_reason = "GATE_REJECT"
                await self._perform_rollback(ctx, reason)
                ctx.succeeded = False
            else:
                projector._atomic_promote(ctx.project_path, staging_path)
                ctx.succeeded = True

        except Exception as e:
            log("KERNEL", f"❌ Fatal kernel error in {ctx.cycle_id}: {e}")
            ctx._telemetry_failure_type = "KERNEL_CRASH"
            ctx._telemetry_termination_reason = str(e)
            await self._perform_rollback(ctx, str(e))
            ctx.succeeded = False
            
            from app.sentinel.verification.verification_gate import VerificationResult
            from app.sentinel.verification.verification_gate import FailureFingerprint
            ctx.verification = VerificationResult(
                project_id=ctx.project_id,
                cycle_id=ctx.cycle_id,
                timestamp=time.time(),
                recommendation="REJECT",
                failure_classification="KERNEL_CRASH",
                verification_score=0.0,
                topology_survival=0.0,
                failures=[
                    FailureFingerprint(
                        failure_type="WIRING_FAILURE" if "WIRING_FAILURE" in str(e) else "KERNEL_CRASH",
                        stage="AST Projection",
                        details=str(e),
                        severity=10.0,
                        nodes_involved=[],
                        suggested_remedy="Trigger fallback mutation."
                    )
                ],
                branch_statistics={"nodes": 0},
                duration_ms=0
            )
        finally:
            if ctx.lease: await self._lease_manager.release(ctx.lease)
            
            if hasattr(ctx, "verification") and ctx.verification and ctx.verification.failures:
                try:
                    FailureAnalyzer.analyze_and_record(ctx.verification.failures)
                except Exception as e:
                    import traceback
                    ValidationRecorder.record_system_event(
                        event_type="ANALYZER_CRASH",
                        severity="ERROR",
                        message=str(e),
                        metadata_json={"trace": traceback.format_exc()}
                    )

            duration_ms = int((time.time() - start_time) * 1000)
            
            final_result = "SUCCESS" if ctx.succeeded else "FAILED"
            termination_reason = getattr(ctx, "_telemetry_termination_reason", "Completed")
            failure_type = getattr(ctx, "_telemetry_failure_type", None)
            
            ValidationRecorder.record_system_event("cycle_completed", "INFO", f"Completed in {duration_ms}ms")
            
            ValidationRecorder.record_projection_run({
                "project_id": ctx.project_id,
                "prompt": "\n".join(ctx.proposed_writes) if ctx.proposed_writes else "",
                "state_fingerprint": graph.graph_hash if hasattr(graph, 'graph_hash') else None,
                "selected_branch": "composite",
                "branch_count": 0,
                "final_weight": 0.0,
                "convergence": 0.0,
                "complexity": len(graph.nodes) if hasattr(graph, 'nodes') else 0,
                "repulsion_score": 0.0,
                "marcus_score": 0.0,
                "memory_hits": 0,
                "dependency_score": 1.0,
                "schema_score": 1.0,
                "state_score": 1.0,
                "build_score": 1.0,
                "runtime_score": 1.0 if ctx.succeeded else 0.0,
                "visual_score": 1.0,
                "topology_score": 1.0,
                "final_result": final_result,
                "failure_type": failure_type,
                "termination_reason": termination_reason,
                "duration_ms": duration_ms
            })
            
            return {
                "success": ctx.succeeded,
                "verification": getattr(ctx, "verification", None),
                "ctx": ctx
            }

    async def lock_substrate_after_scaffold(self, project_id: str, project_path: Path) -> None:
        await SubstrateManager.lock_substrate(project_id=project_id, project_path=project_path)
        log("KERNEL", f"🔒 Substrate locked for {project_id}")

    async def _perform_rollback(self, ctx: ProjectionCycleContext, reason: str) -> None:
        if ctx.transaction: await TransactionEngine.rollback(ctx.transaction, reason)
        if ctx.snapshot: await SnapshotManager(ctx.project_path).restore_snapshot(ctx.snapshot)
        staging_path = ctx.project_path / ".genx_staging"
        if staging_path.exists(): shutil.rmtree(staging_path)

# ─────────────────────────────────────────────────────────────
# 3. Singleton Factory (Defined LAST)
# ─────────────────────────────────────────────────────────────
_KERNEL_INSTANCE: Optional[ExecutionKernel] = None

def get_kernel() -> ExecutionKernel:
    global _KERNEL_INSTANCE
    if _KERNEL_INSTANCE is None:
        _KERNEL_INSTANCE = ExecutionKernel()
    return _KERNEL_INSTANCE