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
from app.models.runtime_models import (
    MutationTier,
    RepairIntent,
    RepairOutcome,
    RepairScope,
    RepairExhaustedSignal,
)
from app.sentinel.runtime.leases import LeaseAcquisitionError, LeaseManager
from app.sentinel.runtime.projection_snapshots import SnapshotManager
from app.sentinel.runtime.transaction_engine import TransactionEngine
from app.substrate.substrate_manager import SubstrateManager
from app.core.exceptions import InfrastructureError
from app.sentinel.verification.verification_gate import SentinelVerificationGate
from app.sentinel.topology.project_graph import ProjectTopologyGraph
from app.sentinel.validation.validation_recorder import ValidationRecorder
from app.sentinel.failure_memory.failure_analyzer import FailureAnalyzer
from app.sentinel.topology.ast_projector import ASTProjector, ProjectorError
import time
from app.sentinel.validation.validation_bus import ValidationBus
from app.sentinel.validation.validation_recorder import ValidationRecorder
from app.sentinel.validation.validation_logger import ValidationLogger
from app.sentinel.config.oracle_policy import OraclePolicy, compute_oracle
from app.sentinel.routing import FailureCategory, SearchOutcome

# ─────────────────────────────────────────────────────────────
# 1. Context (Defined FIRST)
# ─────────────────────────────────────────────────────────────
class MutationPlan:
    def __init__(self, plan_id: str, generated_cycle: int, ttl: int = 1, strategy: str = ""):
        self.plan_id = plan_id
        self.generated_cycle = generated_cycle
        self.ttl = ttl
        self.strategy = strategy


class ProjectionCycleContext:
    def __init__(
        self,
        project_id: str,
        project_path: Path,
        mutation_tier: MutationTier,
        proposed_writes: List[str],
        required_oracle_tiers: Optional[List[str]] = None,
        mutation_plan: Optional[MutationPlan] = None
    ):
        self.cycle_id = str(uuid.uuid4())
        self.project_id = project_id
        self.project_path = project_path
        self.mutation_tier = mutation_tier
        self.proposed_writes = proposed_writes
        self.required_oracle_tiers = required_oracle_tiers or []
        self.mutation_plan = mutation_plan
        self.lease = None
        self.snapshot = None
        self.transaction = None
        self.files_written = []
        self.succeeded = None
        
        # Transition identity fields
        self.e2e_cycle_id = None
        self.parent_transition_id = None
        self.attempt_number = 1

        # ── Phase 3 Routing and Taxonomy Telemetry fields ────
        self.primary_failure_category: Optional[str] = None
        self.active_failure_categories: List[str] = []
        self.routing_decision: Optional[str] = None
        self.routing_reason: Optional[str] = None
        self.search_outcome: Optional[str] = SearchOutcome.NOT_RUN.value

        # ── Phase 5: Atlas Repair Faculty fields ──────────────
        # repair_intent is set by sentinel_runtime before each repair cycle.
        # Scope is kernel-controlled exclusively via current_repair_scope.
        self.repair_intent: Optional[RepairIntent] = None
        self.oracle_before: Optional[float] = None
        self.current_repair_scope: RepairScope = RepairScope.COMPONENT
        self.consecutive_repair_failures: int = 0
        # Failures from the previous cycle; used by projector in repair mode
        self._repair_failures: list = []

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

    async def run_projection_cycle(
        self,
        ctx: ProjectionCycleContext,
        graph: Any,
        llm_client: Any,
        oracle_policy: Optional[OraclePolicy] = None,
    ) -> Dict[str, Any]:
        """Executes the Sentinel atomic control law."""
        log("KERNEL", f"⚡ Projection cycle START: {ctx.cycle_id}")

        start_time = time.time()
        ValidationRecorder.record_system_event("cycle_started", "INFO", f"Starting projection cycle {ctx.cycle_id}")
        
        try:
            ctx.lease = await self._lease_manager.acquire(ctx.project_id, ctx.cycle_id)
            snapshot_mgr = SnapshotManager(ctx.project_path)
            ctx.snapshot = await snapshot_mgr.create_snapshot(ctx.project_id, ctx.cycle_id)

            ctx.transaction = await TransactionEngine.begin(
                ctx.project_id,
                ctx.lease.lease_id,
                ctx.mutation_tier,
                ctx.snapshot.snapshot_id,
                primary_failure_category=ctx.primary_failure_category,
                active_failure_categories=ctx.active_failure_categories,
                routing_decision=ctx.routing_decision,
                routing_reason=ctx.routing_reason,
                search_outcome=ctx.search_outcome
            )

            # Stage 3: Project
            # Resolve effective repair scope (cap applied here, before passing to projector)
            effective_scope: Optional[RepairScope] = None
            if ctx.repair_intent is not None:
                raw_scope = ctx.current_repair_scope
                if oracle_policy is not None:
                    effective_scope = oracle_policy.max_scope_for(len(ctx._repair_failures))
                    # Take the narrower of escalated scope and cap
                    scope_order = [RepairScope.COMPONENT, RepairScope.MODULE, RepairScope.FEATURE, RepairScope.WORKSPACE]
                    raw_idx = scope_order.index(raw_scope) if raw_scope in scope_order else 0
                    cap_idx = scope_order.index(effective_scope) if effective_scope in scope_order else 3
                    effective_scope = scope_order[min(raw_idx, cap_idx)]
                else:
                    effective_scope = raw_scope
                log("KERNEL", f"[REPAIR_SCOPE] current={raw_scope.value} effective={effective_scope.value} "
                              f"failures={len(ctx._repair_failures)}")

            projector = ASTProjector(llm_client=llm_client)
            projection_result = await projector.project(
                ctx,
                graph,
                mutation_plan=ctx.mutation_plan.strategy if ctx.mutation_plan else None,
                repair_intent=ctx.repair_intent,
                repair_scope=effective_scope,
            )
            ctx.files_written = projection_result.get("files_written", [])

            # Stage 4: Gate
            staging_path = ctx.project_path / ".genx_staging"
            verification = SentinelVerificationGate.verify(staging_path, graph)
            ctx.verification = verification

            # Expose the actual failures
            import logging
            logger = logging.getLogger("sentinel")
            for failure in verification.failures:
                logger.info(
                    f"{failure.failure_type} "
                    f"{getattr(failure, 'file', 'None')} "
                    f"{failure.details}"
                )
                log("KERNEL", f"[FAILURE_FINGERPRINT] {failure.failure_type} {getattr(failure, 'file', 'None')} {failure.details}")

            # ── Phase 5: Weighted Oracle Acceptance Check ────────────────
            repair_exhausted: Optional[RepairExhaustedSignal] = None
            if ctx.repair_intent is not None and oracle_policy is not None and ctx.oracle_before is not None:
                oracle_after = compute_oracle(verification.failures, oracle_policy)
                log("KERNEL", f"[ORACLE] before={ctx.oracle_before:.2f} after={oracle_after:.2f} "
                              f"scope={effective_scope.value if effective_scope else 'N/A'}")

                accepted = oracle_after < ctx.oracle_before

                if not accepted:
                    verification.recommendation = "REJECT"
                    verification.failure_classification = "REPAIR_LOSS_NO_IMPROVEMENT"
                    ctx.consecutive_repair_failures += 1
                    log("KERNEL", f"[REPAIR_REJECT] consecutive_failures={ctx.consecutive_repair_failures} "
                                  f"threshold={oracle_policy.scope_escalation_threshold}")

                    if ctx.consecutive_repair_failures >= oracle_policy.scope_escalation_threshold:
                        next_scope = oracle_policy.next_scope(ctx.current_repair_scope)
                        if next_scope is not None:
                            log("KERNEL", f"[SCOPE_ESCALATE] {ctx.current_repair_scope.value} → {next_scope.value}")
                            ctx.current_repair_scope = next_scope
                            ctx.consecutive_repair_failures = 0
                        else:
                            # WORKSPACE exhausted — emit RepairExhaustedSignal, NOT Ω
                            repair_exhausted = RepairExhaustedSignal(
                                project_id=ctx.project_id,
                                cycle_id=ctx.cycle_id,
                                final_oracle=oracle_after,
                            )
                            log("KERNEL", f"[REPAIR_EXHAUSTED] All repair scopes exhausted. "
                                          f"Emitting RepairExhaustedSignal (not Ω). {repair_exhausted}")
                else:
                    # Repair improved oracle — reset scope and counter
                    log("KERNEL", f"[REPAIR_ACCEPT] oracle improved by "
                                  f"{ctx.oracle_before - oracle_after:.2f}. "
                                  f"Resetting scope to COMPONENT.")
                    ctx.consecutive_repair_failures = 0
                    ctx.current_repair_scope = RepairScope.COMPONENT

                # Log RepairOutcome regardless of accept/reject
                from datetime import datetime
                outcome = RepairOutcome(
                    repair_intent=ctx.repair_intent,
                    scope_used=effective_scope or RepairScope.COMPONENT,
                    oracle_before=ctx.oracle_before,
                    oracle_after=oracle_after,
                    accepted=accepted,
                    cycle_id=ctx.cycle_id,
                    timestamp=datetime.utcnow(),
                )
                log("KERNEL", f"[REPAIR_OUTCOME] accepted={outcome.accepted} "
                              f"scope={outcome.scope_used.value} "
                              f"before={outcome.oracle_before:.2f} "
                              f"after={outcome.oracle_after:.2f}")
                # Store on ctx so sentinel_runtime can retrieve the outcome and exhausted signal
                ctx._repair_outcome = outcome
                ctx._repair_exhausted = repair_exhausted

            # S-0.7 Post-Projection Regression Gate: check if projected errors increased compared to correct baseline
            if ctx.repair_intent is not None:
                # During repair cycles, the baseline comparison list is the previous attempt's failures
                parent_failures = ctx._repair_failures
            else:
                # During initial projection, comparison baseline is the in-memory parent graph topology verification failures
                from app.sentinel.verification.verification_gate import SentinelTopologyVerifier
                parent_verification = SentinelTopologyVerifier.verify(graph)
                parent_failures = parent_verification.failures
            child_failures = verification.failures

            parent_set = {
                (f.failure_type, str(getattr(f, 'file_path', getattr(f, 'file', 'None'))))
                for f in parent_failures
            }
            child_set = {
                (f.failure_type, str(getattr(f, 'file_path', getattr(f, 'file', 'None'))))
                for f in child_failures
            }
            resolved = parent_set - child_set
            introduced = child_set - parent_set

            import logging
            logger = logging.getLogger("sentinel")
            logger.info(
                "[S07_DIAGNOSTICS] "
                f"resolved={len(resolved)} "
                f"introduced={len(introduced)} "
                f"net={len(introduced)-len(resolved)}"
            )
            logger.info(f"resolved_failures={list(resolved)}")
            logger.info(f"introduced_failures={list(introduced)}")

            parent_fails = len(parent_failures)
            current_fails = len(child_failures)
            if current_fails > parent_fails:
                log("KERNEL", f"⚠️ S-0.7 Post-Projection Regression Gate: Projected errors increased from {parent_fails} to {current_fails}. Rejecting projection.")
                verification.recommendation = "REJECT"
                verification.failure_classification = "POST_PROJECTION_REGRESSION"

            if verification.recommendation == "REJECT":
                ctx._telemetry_failure_type = verification.failure_classification
                ctx._telemetry_termination_reason = "GATE_REJECT"
                # Defer rollback to let Atlas read .genx_staging first
                ctx.succeeded = False
            else:
                projector._atomic_promote(ctx.project_path, staging_path)
                ctx.succeeded = True

        except ProjectorError as e:
            log("KERNEL", f"⚠️ Projector validation error detected in {ctx.cycle_id}: {e}")
            ctx._telemetry_failure_type = "PROJECTOR_FAILURE"
            ctx._telemetry_termination_reason = f"{e.reason}: {e.details}"
            if ctx.transaction:
                await TransactionEngine.rollback(ctx.transaction, str(e))
            if ctx.snapshot:
                await SnapshotManager(ctx.project_path).restore_snapshot(ctx.snapshot)
            staging_path = ctx.project_path / ".genx_staging"
            if staging_path.exists():
                import shutil
                shutil.rmtree(staging_path)
            ctx.succeeded = False
            
            from app.sentinel.verification.verification_gate import VerificationResult, FailureFingerprint
            ctx.verification = VerificationResult(
                project_id=ctx.project_id,
                cycle_id=ctx.cycle_id,
                timestamp=time.time(),
                recommendation="REJECT",
                failure_classification="PROJECTOR_FAILURE",
                verification_score=0.0,
                topology_survival=0.0,
                failures=[
                    FailureFingerprint(
                        failure_type="PROJECTOR_FAILURE",
                        stage="AST Projection",
                        details=f"{e.reason}: {e.details}",
                        category=FailureCategory.PROJECTOR_FAILURE
                    )
                ],
                branch_statistics={"nodes": 0},
                duration_ms=0
            )

        except InfrastructureError as e:
            log("KERNEL", f"⚠️ Infrastructure error detected in {ctx.cycle_id}: {e}")
            ctx._telemetry_failure_type = "INFRASTRUCTURE_FAILURE"
            ctx._telemetry_termination_reason = str(e)
            if ctx.transaction:
                await TransactionEngine.rollback(ctx.transaction, str(e))
            if ctx.snapshot:
                await SnapshotManager(ctx.project_path).restore_snapshot(ctx.snapshot)
            staging_path = ctx.project_path / ".genx_staging"
            if staging_path.exists():
                import shutil
                shutil.rmtree(staging_path)
            ctx.succeeded = False
            
            from app.sentinel.verification.verification_gate import VerificationResult, FailureFingerprint
            ctx.verification = VerificationResult(
                project_id=ctx.project_id,
                cycle_id=ctx.cycle_id,
                timestamp=time.time(),
                recommendation="REJECT",
                failure_classification="INFRASTRUCTURE_FAILURE",
                verification_score=0.0,
                topology_survival=0.0,
                failures=[
                    FailureFingerprint(
                        failure_type="INFRASTRUCTURE_FAILURE",
                        stage="Execution Kernel",
                        details=str(e),
                        category=FailureCategory.INFRASTRUCTURE_FAILURE
                    )
                ],
                branch_statistics={"nodes": 0},
                duration_ms=0
            )
            ctx._status = "ABORTED_INFRASTRUCTURE"

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
                        category=FailureCategory.UNKNOWN
                    )
                ],
                branch_statistics={"nodes": 0},
                duration_ms=0
            )
        finally:
            if ctx.lease: await self._lease_manager.release(ctx.lease)
            
            if hasattr(ctx, "verification") and ctx.verification and ctx.verification.failures:
                try:
                    # Filter out PROJECTOR_FAILURE from writing to database failure_memory
                    non_memory_failures = [f for f in ctx.verification.failures if f.failure_type != "PROJECTOR_FAILURE"]
                    if non_memory_failures:
                        FailureAnalyzer.analyze_and_record(non_memory_failures)
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
            
            try:
                self._log_repair_mode_transition(ctx)
            except Exception as e:
                log("KERNEL", f"⚠️ Error logging repair transition: {e}")
                
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
                "governance_score": 1.0,
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
                "duration_ms": duration_ms,
                "primary_failure_category": ctx.primary_failure_category,
                "active_failure_categories": ctx.active_failure_categories,
                "routing_decision": ctx.routing_decision,
                "routing_reason": ctx.routing_reason,
                "search_outcome": ctx.search_outcome
            })
            
            res = {
                "success": ctx.succeeded,
                "verification": getattr(ctx, "verification", None),
                "ctx": ctx
            }
            status = getattr(ctx, "_status", None)
            if status:
                res["status"] = status
            return res


    async def lock_substrate_after_scaffold(self, project_id: str, project_path: Path) -> None:
        await SubstrateManager.lock_substrate(project_id=project_id, project_path=project_path)
        log("KERNEL", f"🔒 Substrate locked for {project_id}")

    def _compute_workspace_hash(self, project_path: Path) -> str:
        import hashlib
        import os
        staging_path = project_path / ".genx_staging"
        target_path = staging_path if staging_path.exists() else project_path
        
        hash_obj = hashlib.md5()
        try:
            files = []
            for root, dirs, filenames in os.walk(target_path):
                dirs[:] = [d for d in dirs if d not in (".git", ".venv", "node_modules", "archive", ".pytest_cache", "__pycache__")]
                for f in filenames:
                    files.append(Path(root) / f)
            files.sort()
            for f in files:
                rel_path = f.relative_to(target_path).as_posix()
                try:
                    stat = f.stat()
                    entry = f"{rel_path}:{stat.st_size}:{stat.st_mtime}"
                    hash_obj.update(entry.encode("utf-8"))
                except Exception:
                    pass
        except Exception:
            pass
        return hash_obj.hexdigest()

    def _log_repair_mode_transition(self, ctx: ProjectionCycleContext) -> None:
        import sqlite3
        import json
        import datetime
        from app.sentinel.validation.validation_logger import DB_PATH
        from app.sentinel.topology.ast_projector import _REPAIR_PROMPT, BUILDER_PROMPT
        
        transition_id = ctx.cycle_id
        parent_transition_id = getattr(ctx, "parent_transition_id", None)
        cycle_id = getattr(ctx, "e2e_cycle_id", None) or ctx.cycle_id
        workspace_id = ctx.project_id
        attempt_number = getattr(ctx, "attempt_number", 1)
        workspace_hash = self._compute_workspace_hash(ctx.project_path)
        
        # Oracle / failures
        before_oracle = getattr(ctx, "oracle_before", None)
        if before_oracle is None:
            before_oracle = 0.0
            
        before_failures = []
        before_failures_raw = getattr(ctx, "_repair_failures", [])
        if before_failures_raw:
            for f in before_failures_raw:
                before_failures.append({
                    "failure_type": getattr(f, "failure_type", "UNKNOWN"),
                    "source": str(getattr(f, "source", "")),
                    "stage": getattr(f, "stage", ""),
                    "details": getattr(f, "details", ""),
                    "file": str(getattr(f, "file", "")),
                    "component": getattr(f, "component", None)
                })
        
        before_verification_summary = {
            "failures_count": len(before_failures)
        }
        
        after_failures = []
        after_verification_summary = {}
        after_oracle = 0.0
        
        compiler_output = ""
        bundler_output = ""
        runtime_output = ""
        render_output = ""
        
        verif = getattr(ctx, "verification", None)
        if verif is not None:
            after_failures_raw = getattr(verif, "failures", [])
            for f in after_failures_raw:
                after_failures.append({
                    "failure_type": getattr(f, "failure_type", "UNKNOWN"),
                    "source": str(getattr(f, "source", "")),
                    "stage": getattr(f, "stage", ""),
                    "details": getattr(f, "details", ""),
                    "file": str(getattr(f, "file", "")),
                    "component": getattr(f, "component", None)
                })
            after_verification_summary = {
                "recommendation": getattr(verif, "recommendation", None),
                "failure_classification": getattr(verif, "failure_classification", None),
                "score": getattr(verif, "verification_score", 0.0)
            }
            compiler_output = getattr(verif, "compiler_output", "") or ""
            bundler_output = getattr(verif, "bundler_output", "") or ""
            runtime_output = getattr(verif, "runtime_output", "") or ""
            render_output = getattr(verif, "render_output", "") or ""
            
            try:
                from app.sentinel.config.oracle_policy import get_oracle_policy, compute_oracle
                policy = get_oracle_policy()
                after_oracle = compute_oracle(after_failures_raw, policy) if after_failures_raw else 0.0
            except Exception:
                after_oracle = float(len(after_failures_raw))
        else:
            after_oracle = 0.0 if ctx.succeeded else before_oracle
            
        target_file = None
        instruction = None
        repair_mode = "INITIAL_PROJECTION"
        system_prompt = None
        user_message = None
        scope = None
        
        if getattr(ctx, "repair_intent", None) is not None:
            intent = ctx.repair_intent
            target_file = str(intent.target_file) if intent.target_file else None
            instruction = intent.instruction
            scope = getattr(ctx, "current_repair_scope", None)
            if scope == RepairScope.COMPONENT:
                repair_mode = "COMPONENT_REPAIR"
            elif scope == RepairScope.MODULE:
                repair_mode = "MODULE_REPAIR"
            elif scope == RepairScope.FEATURE:
                repair_mode = "FEATURE_REPAIR"
            elif scope == RepairScope.WORKSPACE:
                repair_mode = "WORKSPACE_REPAIR"
            
            system_prompt = _REPAIR_PROMPT
            user_message = getattr(ctx, "_repair_prompt", None)
        else:
            user_message = getattr(ctx, "_initial_prompt", None)
            system_prompt = BUILDER_PROMPT
            
        try:
            # 1. Fetch verbatim source content and compute unified diff
            before_source = None
            after_source = None
            diff = None
            if target_file:
                workspace_file_path = ctx.project_path / target_file
                staging_file_path = ctx.project_path / ".genx_staging" / target_file
                
                if workspace_file_path.exists() and workspace_file_path.is_file():
                    try:
                        with open(workspace_file_path, "r", encoding="utf-8", errors="replace") as f_in:
                            before_source = f_in.read()
                    except Exception as read_err:
                        log("KERNEL", f"⚠️ Error reading before_source: {read_err}")
                        
                if staging_file_path.exists() and staging_file_path.is_file():
                    try:
                        with open(staging_file_path, "r", encoding="utf-8", errors="replace") as f_in:
                            after_source = f_in.read()
                    except Exception as read_err:
                        log("KERNEL", f"⚠️ Error reading after_source: {read_err}")
                elif before_source is not None:
                    after_source = before_source
                    
                if before_source is not None and after_source is not None:
                    import difflib
                    diff_lines = list(difflib.unified_diff(
                        before_source.splitlines(keepends=True),
                        after_source.splitlines(keepends=True),
                        fromfile=f"a/{target_file}",
                        tofile=f"b/{target_file}"
                    ))
                    diff = "".join(diff_lines)

            # 2. Write to sentinel_experience.db via ExperienceMemoryAccessLayer
            try:
                from app.sentinel.experience.memory_access_layer import ExperienceMemoryAccessLayer
                exp_mal = ExperienceMemoryAccessLayer()
                scope_str = scope.name if hasattr(scope, "name") else str(scope) if scope else None
                exp_mal.insert_transition(
                    transition_id=transition_id,
                    parent_transition_id=parent_transition_id,
                    cycle_id=cycle_id,
                    workspace_id=workspace_id,
                    attempt_number=attempt_number,
                    workspace_hash=workspace_hash,
                    before_oracle=before_oracle,
                    after_oracle=after_oracle,
                    before_failures=before_failures,
                    after_failures=after_failures,
                    before_verification_summary=before_verification_summary,
                    after_verification_summary=after_verification_summary,
                    target_file=target_file,
                    scope=scope_str,
                    repair_mode=repair_mode,
                    instruction=instruction,
                    prompt=system_prompt,
                    context_metadata={"user_message": user_message},
                    before_source=before_source,
                    after_source=after_source,
                    diff=diff,
                    compiler_output=compiler_output,
                    bundler_output=bundler_output,
                    runtime_output=runtime_output,
                    render_output=render_output
                )
            except Exception as exp_err:
                log("KERNEL", f"⚠️ Failed to insert experience transition: {exp_err}")

            # 3. Legacy write to flat repair_mode_transitions (sentinel_validation V2.db)
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS repair_mode_transitions (
                transition_id TEXT PRIMARY KEY,
                parent_transition_id TEXT,
                cycle_id TEXT,
                workspace_id TEXT,
                attempt_number INTEGER,
                workspace_hash TEXT,
                before_oracle REAL,
                after_oracle REAL,
                before_failures TEXT,
                after_failures TEXT,
                before_verification_summary TEXT,
                after_verification_summary TEXT,
                target_file TEXT,
                repair_mode TEXT,
                instruction TEXT,
                system_prompt TEXT,
                user_message TEXT,
                compiler_output TEXT,
                bundler_output TEXT,
                runtime_output TEXT,
                render_output TEXT,
                timestamp DATETIME
            )
            """)
            
            cursor.execute("""
            INSERT OR REPLACE INTO repair_mode_transitions (
                transition_id, parent_transition_id, cycle_id, workspace_id, attempt_number,
                workspace_hash, before_oracle, after_oracle, before_failures, after_failures,
                before_verification_summary, after_verification_summary, target_file, repair_mode,
                instruction, system_prompt, user_message, compiler_output, bundler_output,
                runtime_output, render_output, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                transition_id,
                parent_transition_id,
                cycle_id,
                workspace_id,
                attempt_number,
                workspace_hash,
                before_oracle,
                after_oracle,
                json.dumps(before_failures),
                json.dumps(after_failures),
                json.dumps(before_verification_summary),
                json.dumps(after_verification_summary),
                target_file,
                repair_mode,
                instruction,
                system_prompt,
                user_message,
                compiler_output,
                bundler_output,
                runtime_output,
                render_output,
                datetime.datetime.utcnow().isoformat()
            ))
            conn.commit()
            conn.close()
            log("KERNEL", f"📊 Logged repair transition {transition_id} (Attempt {attempt_number}, Mode: {repair_mode}, before={before_oracle:.2f}, after={after_oracle:.2f})")
        except Exception as db_err:
            log("KERNEL", f"⚠️ Failed to log repair transition: {db_err}")

    async def rollback_cycle(self, ctx: ProjectionCycleContext, reason: str) -> None:
        """Public entry point to roll back a failed projection cycle."""
        await self._perform_rollback(ctx, reason)

    async def _perform_rollback(self, ctx: ProjectionCycleContext, reason: str) -> None:
        if ctx.transaction: await TransactionEngine.rollback(ctx.transaction, reason)
        if ctx.snapshot: await SnapshotManager(ctx.project_path).restore_snapshot(ctx.snapshot)
        staging_path = ctx.project_path / ".genx_staging"
        if staging_path.exists():
            # Save rejected projections: archive workspace/ instead of deleting it
            archive_dir = ctx.project_path.parent / "archive" / f"{ctx.project_id}_rejected_{int(time.time())}"
            try:
                shutil.copytree(staging_path, archive_dir, dirs_exist_ok=True)
                log("KERNEL", f"💾 Archived rejected projection workspace to: {archive_dir}")
            except Exception as archive_err:
                log("KERNEL", f"⚠️ Failed to archive staging directory: {archive_err}")
            # Keep staging path alive for repair mode attempts. Cleaned up at the end of sentinel_runtime E2E loop.
            # shutil.rmtree(staging_path)

# ─────────────────────────────────────────────────────────────
# 3. Singleton Factory (Defined LAST)
# ─────────────────────────────────────────────────────────────
_KERNEL_INSTANCE: Optional[ExecutionKernel] = None

def get_kernel() -> ExecutionKernel:
    global _KERNEL_INSTANCE
    if _KERNEL_INSTANCE is None:
        _KERNEL_INSTANCE = ExecutionKernel()
    return _KERNEL_INSTANCE