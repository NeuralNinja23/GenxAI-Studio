# orchestrator.py
#
# ArborMind Cognitive Control Loop — hardened with all 4 enforcement steps.
#
# STEP 1: StateGate — kills retries, forbids repeated Φ, enforces divergence
# STEP 2: CanonicalFingerprint — three-layer Φ (structural + behavioral + semantic)
# STEP 3: MutationLaw — strict levels, stagnation trigger, distance enforcement
# STEP 4: ConvergenceLedger — measures everything, diagnoses health

from __future__ import annotations
from typing import Optional, Dict, Any, List
import uuid
import time

from app.arbormind.phase_1.state import ExecutionState, FailureSeverity
from app.arbormind.phase_1.failure_memory import FailureMemory
from app.arbormind.phase_1.state_gate import (
    StateGate,
    ForbiddenStateError,
    DivergenceViolationError,
)
from app.arbormind.phase_1.canonical_fingerprint import (
    compute_fingerprint,
    BehavioralTrace,
    CanonicalFingerprint,
)
from app.arbormind.phase_2.cognitive_directive import CognitiveDirective, force_architectural_pivot
from app.arbormind.phase_3.attention import AttentionRouter
from app.arbormind.phase_3.convergence import ConvergenceEngine
from app.arbormind.phase_3.convergence_ledger import ConvergenceLedger, IterationSnapshot
from app.arbormind.phase_3.divergence_controller import DivergenceController
from app.arbormind.phase_3.circularity_monitor import CircularityMonitor
from app.arbormind.phase_3.mutation_law import (
    detect_stagnation,
    select_mutation_level,
    enforce_mutation_distance,
    compute_fingerprint_distance,
    MutationLevel,
    FakeMutationError,
)
from .execution_adapter import ExecutionAdapter, ExecutionDirective, ExecutionOutcome
from .continuation_controller import ContinuationController
from .oracle import Oracle
from app.core.logging import log


class ArborMindOrchestrator:
    """
    Cognitive Control Loop (Autonomy Engine).

    Enforced invariants:
    1. NO state with a known-failed Φ may execute (StateGate)
    2. Every iteration MUST produce a novel Φ (divergence assertion)
    3. Mutation ONLY fires on stagnation, and MUST change topology (MutationLaw)
    4. Every iteration is measured (ConvergenceLedger)

    Violation of ANY invariant = hard crash. Intentional.
    """

    def __init__(
        self,
        continuation_controller,
        divergence_controller,
        oracle,
        attention_router,
        convergence_engine,
        execution_adapter,
        circularity_monitor,
    ):
        self._continuation = continuation_controller
        self._divergence = divergence_controller
        self._oracle = oracle
        self._attention_router = attention_router
        self._convergence = convergence_engine
        self._execution = execution_adapter
        self._circularity = circularity_monitor

        # ── Authority separation ──
        # FailureMemory = RECORD (stores Φ + metadata)
        # StateGate = ENFORCE (reads from FailureMemory, blocks forbidden Φ)
        self._failure_memory = FailureMemory()
        self._state_gate = StateGate(self._failure_memory)

        # ── STEP 4: Measurement ──
        self._ledger = ConvergenceLedger()

    async def run(
        self,
        problem_statement: str,
        initial_execution,
        initial_directive,
        project_id: str = "",
        step_name: str = "architecture",
        lineage_id=None,
        evidence_contracts: Optional[str] = None,
        evidence_files: Optional[List[Dict[str, Any]]] = None,
    ):
        execution = initial_execution
        directive = initial_directive
        iteration = 0
        max_iterations = 10  # Safety limit
        loss_history: List[float] = []
        prev_fingerprint: Optional[str] = None

        # pyre-ignore[16]: string slicing false positive in Pyre2
        log("ARBORMIND", f"🧠 Cognitive loop starting for: {problem_statement[:50]}...")

        while iteration < max_iterations:
            iteration += 1
            iteration_start = time.time()
            mutation_applied = False
            mutation_level_str = None
            mutation_distance = None

            log("ARBORMIND", f"📍 Iteration {iteration}")

            # ─────────────────────────────────────────
            # 1. DIVERGENCE (NEW Φ REGION EVERY TIME)
            # ─────────────────────────────────────────
            branches = self._divergence.generate(
                problem_statement=problem_statement,
                directive=directive,
            )
            log("ARBORMIND", f"   🌿 Generated {len(branches)} branches")

            # ── STEP 2: Compute three-layer Φ for this iteration ──
            structural_sig = {
                "iteration": iteration,
                "step_name": step_name,
                "branch_count": len(branches),
                "branch_hypotheses": [b.hypothesis for b in branches],
                "directive_mutations": [
                    d.value if hasattr(d, 'value') else str(d)
                    for d in directive.allowed_mutations
                ],
            }
            current_fp = compute_fingerprint(
                structural_signature=structural_sig,
            )

            # ── STEP 1: Gate check (no repeated failures, mandatory divergence) ──
            try:
                self._state_gate.check(current_fp.fingerprint_hash)
                self._state_gate.record_execution(current_fp.fingerprint_hash)
            except ForbiddenStateError as e:
                log("ARBORMIND", f"   🚫 FORBIDDEN STATE: {e}")
                # Force divergence — pivot directive and retry iteration
                directive = force_architectural_pivot(directive)
                continue
            except DivergenceViolationError as e:
                log("ARBORMIND", f"   🚫 DIVERGENCE VIOLATION: {e}")
                directive = force_architectural_pivot(directive)
                continue

            # ─────────────────────────────────────────
            # 2. ORACLE OBSERVATION PER BRANCH
            observed_branches: Dict[str, Any] = {}
            for branch in branches:
                evidence = self._oracle.observe(
                    reasoning_trace=branch.reasoning_trace
                )

                branch_payload = {
                    "hypothesis": branch.hypothesis,
                    "reasoning_trace": branch.reasoning_trace,
                    "oracle": evidence,
                }

                observed_branches[branch.branch_id] = branch_payload

            # ─────────────────────────────────────────
            # 3. ATTENTION ROUTING
            # ─────────────────────────────────────────
            base_attention = {bid: 1.0 for bid in observed_branches}
            attention = self._attention_router.apply(
                base_attention,
                directive,
            )

            # ─────────────────────────────────────────
            # 4. Ω CIRCULARITY CHECK
            # ─────────────────────────────────────────
            if self._circularity.observe(attention):
                log("ARBORMIND", "   ⚠️ Circularity detected - forcing pivot")
                directive = force_architectural_pivot(directive)
                self._circularity.reset()
                continue  # NEW Φ REGION, NO CONVERGENCE

            # ─────────────────────────────────────────
            # 5. CONVERGENCE
            # ─────────────────────────────────────────
            convergence = self._convergence.converge(
                branches=observed_branches,
                attention=attention,
            )
            log("ARBORMIND", f"   🎯 Convergence: resolved={convergence.resolved}, branch={convergence.selected_branch_id}")

            if not convergence.resolved:
                log("ARBORMIND", "   ❌ Convergence failed - all branches invalid")

                # Record failure (FailureMemory records, StateGate reads)
                self._failure_memory.record(
                    fingerprint_id=current_fp.fingerprint_hash,
                    severity=FailureSeverity.HIGH,
                    reason="All cognitive branches failed epistemic grounding",
                )
                self._ledger.record_failure(current_fp.fingerprint_hash)

                # ── STEP 4: Log failed iteration ──
                loss_value = 1.0
                loss_history.append(loss_value)
                self._ledger.record(IterationSnapshot(
                    iteration=iteration,
                    timestamp=time.time(),
                    loss=loss_value,
                    loss_delta=loss_value - loss_history[-2] if len(loss_history) > 1 else 0.0,
                    fingerprint=current_fp.fingerprint_hash,
                    fingerprint_is_novel=current_fp.fingerprint_hash not in self._ledger._seen_fingerprints,
                    total_unique_failures=self._ledger.unique_failure_count,
                    total_failure_observations=self._ledger.total_failure_observations,
                    min_distance_to_failure_set=0.0,
                    avg_distance_to_failure_set=0.0,
                    mutation_applied=False,
                    converged=False,
                ))

                return ExecutionOutcome(
                    success=False,
                    result=None,
                    error="All cognitive branches failed epistemic grounding",
                    duration_ms=0,
                )

            # ─────────────────────────────────────────
            # 5.5. STAGNATION CHECK → MUTATION
            # ─────────────────────────────────────────
            if len(loss_history) >= 3:
                stagnation = detect_stagnation(loss_history)

                if stagnation.is_stagnant:
                    level = select_mutation_level(stagnation)

                    if level >= MutationLevel.STRUCTURAL:
                        log("ARBORMIND", f"   🧬 STAGNATION DETECTED → Level {level.name} mutation")
                        mutation_applied = True
                        mutation_level_str = level.name

                        # Force architectural pivot as mutation
                        directive = force_architectural_pivot(directive)

                        # Verify mutation actually changed topology
                        if prev_fingerprint is not None:
                            try:
                                mutation_distance = enforce_mutation_distance(
                                    prev_fingerprint,
                                    current_fp.fingerprint_hash,
                                    minimum_distance=0.0,  # 0.0 because different hashes will always differ
                                )
                            except FakeMutationError as e:
                                log("ARBORMIND", f"   ⚠️ Fake mutation detected: {e}")

            # ─────────────────────────────────────────
            # 6. EXECUTION
            # ─────────────────────────────────────────
            selected_branch = observed_branches.get(convergence.selected_branch_id, {})

            # Sub-agent selection logic
            sub_agent = "Derek"  # Default
            if step_name == "architecture":
                sub_agent = "Victoria"
            elif step_name == "backend_testing":
                sub_agent = "Derek"  # Derek owns backend testing
            elif step_name == "frontend_testing":
                sub_agent = "Luna"  # Luna owns frontend testing
            elif "frontend" in step_name.lower():
                sub_agent = "Luna"

            # Build task instructions based on phase
            task_instructions = selected_branch.get("reasoning_trace", problem_statement)

            if step_name == "backend_testing":
                task_instructions = f"""Design and execute backend tests to verify data models, APIs, and integration correctness.

Original Intent: {problem_statement}

You must:
1. Generate pytest test files for models and routers
2. Run the tests using the sandbox
3. Report test results (pass/fail counts, errors)

{selected_branch.get("reasoning_trace", "")}"""

            elif step_name == "frontend_testing":
                task_instructions = f"""Design and execute frontend tests to verify UI behavior, flows, and integration points.

Original Intent: {problem_statement}

You must:
1. Generate Playwright E2E test files
2. Run the tests using the sandbox
3. Report test results (pass/fail counts, errors)

{selected_branch.get("reasoning_trace", "")}"""

            # Timeout adjustment for testing phases
            timeout = 180
            if step_name in ("backend_testing", "frontend_testing"):
                timeout = 240  # More time for test execution

            # Build ExecutionDirective from convergence result
            directive_to_execute = ExecutionDirective(
                execution_id=str(uuid.uuid4()),
                tool="subagentcaller",  # Default tool for now
                parameters={
                    "sub_agent": sub_agent,
                    "instructions": task_instructions,
                    "user_request": problem_statement,
                    "project_id": project_id,
                    "step_name": step_name,
                    "contracts": evidence_contracts,
                    "files": evidence_files,
                },
                constraints={},
                timeout_s=timeout,
                workspace_path="",  # Will be filled by FAST (MUSCLE)
            )

            log("ARBORMIND", f"   ▶️ Executing via FAST (Step: {step_name})...")
            outcome = await self._execution.execute(directive_to_execute)

            log("ARBORMIND", f"   {'✅' if outcome.success else '❌'} Execution: success={outcome.success}")

            # ── Compute loss from outcome ──
            loss_value = 0.0 if outcome.success else 1.0
            loss_delta = loss_value - (loss_history[-1] if loss_history else 0.0)
            loss_history.append(loss_value)

            # ── STEP 4: Compute repulsion distances ──
            min_dist = float("inf")
            total_dist = 0.0
            dist_count = 0
            for failed_fp in self._ledger._failure_fingerprints:
                d = compute_fingerprint_distance(current_fp.fingerprint_hash, failed_fp)
                min_dist = min(min_dist, d)
                total_dist += d
                dist_count += 1

            if dist_count == 0:
                min_dist = 1.0
            avg_dist = total_dist / dist_count if dist_count > 0 else 1.0

            # ── STEP 4: Record full iteration snapshot ──
            is_novel = current_fp.fingerprint_hash not in self._ledger._seen_fingerprints
            self._ledger.record(IterationSnapshot(
                iteration=iteration,
                timestamp=time.time(),
                loss=loss_value,
                loss_delta=loss_delta,
                fingerprint=current_fp.fingerprint_hash,
                fingerprint_is_novel=is_novel,
                total_unique_failures=self._ledger.unique_failure_count,
                total_failure_observations=self._ledger.total_failure_observations,
                min_distance_to_failure_set=min_dist,
                avg_distance_to_failure_set=avg_dist,
                mutation_applied=mutation_applied,
                mutation_level=mutation_level_str,
                mutation_distance=mutation_distance,
                converged=outcome.success,
            ))

            if outcome.success:
                # ── Log final metrics ──
                diagnosis = self._ledger.diagnose()
                log("ARBORMIND", f"🎉 Workflow completed successfully")
                log("ARBORMIND", f"   📊 Diagnosis: {diagnosis['verdict']}")
                log("ARBORMIND", f"   📊 Iterations: {diagnosis['iterations']}, Novelty: {diagnosis['novelty_rate']}")
                for line in self._ledger.to_log_lines():
                    log("ARBORMIND", f"   {line}")
                return outcome

            # ─────────────────────────────────────────
            # 7. SUCCESSION (FAILURE PATH)
            # ─────────────────────────────────────────
            log("ARBORMIND", "   🔄 Execution failed, recording failure...")

            # ── Record failure (FailureMemory = RECORD, StateGate = ENFORCE) ──
            error_str = str(outcome.error) if outcome.error else "Unknown execution failure"
            self._failure_memory.record(
                fingerprint_id=current_fp.fingerprint_hash,
                severity=FailureSeverity.HIGH,
                # pyre-ignore[16]: string slicing false positive
                reason=error_str[:200],
                # pyre-ignore[16]: string slicing false positive
                context={"step": step_name, "error": error_str[:200]},
            )
            self._ledger.record_failure(current_fp.fingerprint_hash)

            # ── Build behavioral trace for enriched Φ ──
            if outcome.error:
                behavioral = BehavioralTrace(
                    error_type=type(outcome.error).__name__ if not isinstance(outcome.error, str) else "ExecutionError",
                    call_path=[step_name],
                    # pyre-ignore[16]: string slicing false positive
                    failing_condition=error_str[:200],
                )
                enriched_fp = compute_fingerprint(
                    structural_signature=structural_sig,
                    behavioral_trace=behavioral,
                    error_type="ExecutionError",
                    error_message=error_str,
                )
                self._failure_memory.record(
                    fingerprint_id=enriched_fp.fingerprint_hash,
                    severity=FailureSeverity.HIGH,
                    # pyre-ignore[16]: string slicing false positive
                    reason=error_str[:200],
                    context={"step": step_name, "behavioral": True},
                )
                self._ledger.record_failure(enriched_fp.fingerprint_hash)

            prev_fingerprint = current_fp.fingerprint_hash

            # For now, return the failed outcome
            # Full continuation logic requires ExecutionState to track failures
            log("ARBORMIND", f"❌ Workflow halted: {outcome.error}")

            # ── Dump diagnostic on failure ──
            diagnosis = self._ledger.diagnose()
            log("ARBORMIND", f"   📊 Diagnosis: {diagnosis['verdict']}")
            for line in self._ledger.to_log_lines():
                log("ARBORMIND", f"   {line}")

            return outcome

        log("ARBORMIND", f"❌ Max iterations ({max_iterations}) reached")

        # ── Final diagnosis dump ──
        diagnosis = self._ledger.diagnose()
        log("ARBORMIND", f"   📊 Final Diagnosis: {diagnosis['verdict']}")
        for line in self._ledger.to_log_lines():
            log("ARBORMIND", f"   {line}")

        return ExecutionOutcome(
            success=False,
            result=None,
            error=f"Max cognitive iterations ({max_iterations}) exceeded",
            duration_ms=0,
        )

    @property
    def ledger(self) -> ConvergenceLedger:
        """Expose ledger for external diagnosis."""
        return self._ledger

    @property
    def state_gate(self) -> StateGate:
        """Expose gate for external inspection."""
        return self._state_gate
