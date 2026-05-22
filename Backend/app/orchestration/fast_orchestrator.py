# app/orchestration/fast_orchestrator.py
"""
FAST v2 - Pure Execution Engine

FAST is muscle. ArborMind is brain.

FAST:
- Executes exactly one tool per call
- Returns outcome
- Never plans, branches, validates, interprets, or halts

ArborMind:
- Owns Φ, Ω, α
- Owns divergence, stagnation detection, succession, termination
- Sends ExecutionDirective
- Receives ExecutionOutcome
"""

from typing import Any, Dict, List, Optional
import sys
from pathlib import Path

# Add the Backend folder to python path so 'app' module can be resolved 
# when clicking 'Run Python File' in VS Code
backend_root = str(Path(__file__).resolve().parent.parent.parent)
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from app.core.logging import log
from app.orchestration.state import WorkflowStateManager


class FASTExecutor:
    """
    Pure execution engine.

    The ONLY interface ArborMind uses to execute tools.
    No planning. No branching. No validation. No halting decisions.
    """

    def __init__(
        self,
        project_id: str,
        project_path: Path,
        manager: Any = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.project_id = project_id
        self.project_path = project_path
        self.manager = manager
        self.provider = provider
        self.model = model

    async def execute_once(
        self,
        tool: str,
        parameters: Dict[str, Any],
        constraints: Dict[str, Any],
        timeout: int,
    ):
        """
        Execute a single tool. No loops. No opinions. No planning.

        This is the ONLY method ArborMind is allowed to call.

        Contract:
        - Receive FULLY RESOLVED parameters
        - Execute exactly ONE tool
        - Return outcome
        - NEVER plan, branch, validate, interpret, or halt

        ArborMind owns: Φ, Ω, α, divergence, stagnation, succession, termination
        FAST owns: execution (nothing else)
        """
        from app.arbormind.adapters.execution_adapter import ExecutionOutcome
        from app.tools.registry import run_tool
        import time

        start = time.time()

        log("FAST", f"▶️ Executing tool: {tool}")

        try:
            # Direct tool call - NO PLANNING, NO BRANCHING
            # Parameters must be FULLY RESOLVED by ArborMind
            tool_args = {
                **parameters,
                "project_path": str(self.project_path),
                "project_id": self.project_id,
            }

            # Apply constraints
            if timeout > 0:
                tool_args["timeout"] = timeout

            # Execute the tool DIRECTLY
            result = await run_tool(name=tool, args=tool_args)

            duration_ms = int((time.time() - start) * 1000)

            # Determine success from tool result
            success = result.get("passed", False) or result.get("success", False)

            # ════════════════════════════════════════════════════════
            # ARTIFACT PERSISTENCE (FAST = Muscle)
            # ════════════════════════════════════════════════════════
            files_persisted = 0
            if success:
                output = result.get("output", {})
                if isinstance(output, dict) and "files" in output:
                    files = output["files"]
                    for f in files:
                        path = f.get("path")
                        content = f.get("content")
                        if path and content:
                            try:
                                full_path = self.project_path / path
                                full_path.parent.mkdir(parents=True, exist_ok=True)
                                with open(full_path, "w", encoding="utf-8") as file:
                                    file.write(content)
                                files_persisted += 1
                            except Exception as pe:
                                log("FAST", f"⚠️ Failed to persist {path}: {pe}")

            log("FAST", f"{'✅' if success else '❌'} Tool {tool} completed in {duration_ms}ms (Persisted: {files_persisted})")

            return ExecutionOutcome(
                success=success,
                result=result,
                error=result.get("error") if not success else None,
                duration_ms=duration_ms,
            )


        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            log("FAST", f"❌ Tool {tool} failed: {e}")
            return ExecutionOutcome(
                success=False,
                result=None,
                error=str(e),
                duration_ms=duration_ms,
            )


# Alias for backward compatibility during transition
FASTOrchestratorV2 = FASTExecutor


async def run_arbormind_workflow(
    project_id: str,
    manager: Any,
    project_path: Path,
    user_request: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> None:
    """
    Run a workflow via ArborMind.

    ArborMind controls:
    - What to execute
    - When to retry (via new lineage, not retry)
    - When to halt
    - Failure classification and mutation

    FAST just executes.
    """
    from app.arbormind.adapters.orchestrator import ArborMindOrchestrator
    from app.arbormind.adapters.execution_adapter import ExecutionAdapter, ExecutionDirective
    from app.arbormind.adapters.continuation_controller import ContinuationController
    from app.arbormind.adapters.oracle import OracleSupervisor
    from app.arbormind.phase_1.state import ExecutionState
    from app.arbormind.phase_1.failure_memory import FailureMemory
    from app.arbormind.phase_2.cognitive_directive import CognitiveDirective
    from app.arbormind.phase_2.failure_taxonomy import FailureTaxonomy
    from app.arbormind.phase_2.mutation_authority import MutationAuthority
    from app.arbormind.phase_2.attention_bias import AttentionBiasEngine
    from app.arbormind.phase_3.attention import AttentionRouter
    from app.arbormind.phase_3.convergence import ConvergenceKernel
    from app.arbormind.phase_3.divergence_controller import DivergenceController
    from app.arbormind.phase_3.circularity_monitor import CircularityMonitor
    from app.arbormind.phase_3.validity import ValidityEvaluator
    from app.arbormind.adapters.lineage_tracker import LineageTracker

    log("ARBORMIND", f"▶️ Starting cognitive loop for: {user_request[:50]}...")

    # ─────────────────────────────────────────────────────────────────────────
    # 1. CREATE FAST EXECUTOR
    # ─────────────────────────────────────────────────────────────────────────
    fast = FASTExecutor(
        project_id=project_id,
        project_path=project_path,
        manager=manager,
        provider=provider,
        model=model,
    )
    execution_adapter = ExecutionAdapter(fast)

    # ─────────────────────────────────────────────────────────────────────────
    # 2. CREATE PHASE 1 COMPONENTS (Failure Memory)
    # ─────────────────────────────────────────────────────────────────────────
    failure_memory = FailureMemory()

    # ─────────────────────────────────────────────────────────────────────────
    # 3. CREATE PHASE 2 COMPONENTS (Taxonomy, Authority, Bias)
    # ─────────────────────────────────────────────────────────────────────────
    failure_taxonomy = FailureTaxonomy()
    mutation_authority = MutationAuthority()
    attention_bias = AttentionBiasEngine()
    lineage_tracker = LineageTracker()

    # ─────────────────────────────────────────────────────────────────────────
    # 4. CREATE CONTINUATION CONTROLLER
    # ─────────────────────────────────────────────────────────────────────────
    continuation_controller = ContinuationController(
        failure_memory=failure_memory,
        lineage_tracker=lineage_tracker,
        taxonomy=failure_taxonomy,
        mutation_authority=mutation_authority,
        attention_bias_engine=attention_bias,
    )


    # ─────────────────────────────────────────────────────────────────────────
    # 5. CREATE PHASE 3 COMPONENTS
    # ─────────────────────────────────────────────────────────────────────────
    # Divergence Controller (needs LLM - placeholder for now)
    divergence_controller = DivergenceController(llm=None)

    # Oracle (multimodal witness)
    oracle = OracleSupervisor(project_path=str(project_path))

    # Attention Router
    attention_router = AttentionRouter()

    # Validity Evaluator
    validity_evaluator = ValidityEvaluator()

    # Convergence Engine
    convergence_engine = ConvergenceKernel(validator=validity_evaluator)


    # Circularity Monitor
    circularity_monitor = CircularityMonitor(patience=3, epsilon=0.01)

    # ─────────────────────────────────────────────────────────────────────────
    # 6. CREATE ARBORMIND ORCHESTRATOR
    # ─────────────────────────────────────────────────────────────────────────
    orchestrator = ArborMindOrchestrator(
        continuation_controller=continuation_controller,
        divergence_controller=divergence_controller,
        oracle=oracle,
        attention_router=attention_router,
        convergence_engine=convergence_engine,
        execution_adapter=execution_adapter,
        circularity_monitor=circularity_monitor,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 7. WORKFLOW GOVERNOR (Outer Procedural Loop)
    # ─────────────────────────────────────────────────────────────────────────
    phases = [
        "architecture",
        "backend_models",
        "backend_routers",
        "frontend_mock",
        "system_integration",
        
        # Testing phases (separate, not merged)
        "backend_testing",    # Derek
        "frontend_testing",   # Luna
    ]

    
    evidence_contracts = ""
    evidence_files = [] 
    evidence_reviews = []  # Store ReviewReports as evidence
    
    # Import review function
    from app.orchestration.phase_review import run_phase_review
    from app.orchestration.review_report import ReviewReport
    
    # RESUME SUPPORT: Check what's already done
    completed_steps = await WorkflowStateManager.get_completed_steps(project_id) or []
    if completed_steps:
        log("ARBORMIND", f"🔄 Resuming workflow from checkpoint. Completed: {', '.join(completed_steps)}")

    for phase in phases:
        # SKIP LOGIC
        if phase in completed_steps:
            log("ARBORMIND", f"⏭️ Skipping completed phase: {phase}")
            # Still need to harvest if it's architecture for downstream context
            if phase == "architecture":
                evidence_contracts = _collect_evidence_contracts(project_path)
            continue

        log("ARBORMIND", f"🏁 PHASE START: {phase}")

        initial_execution = ExecutionState()
        initial_directive = CognitiveDirective()
        
        # Build combined evidence: contracts + prior reviews
        combined_evidence = evidence_contracts
        if evidence_reviews:
            combined_evidence += "\n\n# Prior Phase Reviews:\n"
            for review in evidence_reviews[-3:]:  # Last 3 reviews
                combined_evidence += f"\n{review.to_evidence_string()}\n"

        try:
            outcome = await orchestrator.run(
                problem_statement=user_request,
                initial_execution=initial_execution,
                initial_directive=initial_directive,
                project_id=project_id,
                step_name=phase,
                evidence_contracts=combined_evidence,  # Now includes reviews
                evidence_files=None, 
            )
            
            if not outcome.success:
                log("ARBORMIND", f"❌ Workflow halted at phase '{phase}': {outcome.error}")
                break # TERMINATE WORKFLOW
            
            log("ARBORMIND", f"✅ Phase '{phase}' completed successfully")
            
            # Persist progress
            await WorkflowStateManager.save_completed_step(project_id, phase)

            # Post-phase artifact harvesting (Immersion of Evidence)
            if phase == "architecture":
                evidence_contracts = _collect_evidence_contracts(project_path)
                log("ARBORMIND", f"📥 Harvested architecture as evidence for downstream phases.")
            
            # ═══════════════════════════════════════════════════════════════
            # POST-PHASE REVIEW HOOK (Marcus observes, never controls)
            # ═══════════════════════════════════════════════════════════════
            phase_artifacts = _collect_phase_artifacts(project_path, phase)
            
            review = await run_phase_review(
                phase_name=phase,
                artifacts=phase_artifacts,
                intent=user_request,
                prior_reviews=evidence_reviews,
            )
            
            # Store review as evidence (never gate on it)
            evidence_reviews.append(review)
            log("ARBORMIND", f"📝 Review stored for phase '{phase}'")

        except Exception as e:
            log("ARBORMIND", f"❌ Cognitive loop crashed in phase '{phase}': {e}")
            import traceback
            traceback.print_exc()
            break


    log("ARBORMIND", "🏁 Workflow governor finished.")
    
    # ─────────────────────────────────────────────────────────────────────────
    # 8. POST-WORKFLOW: SANDBOX INITIALIZATION
    # ─────────────────────────────────────────────────────────────────────────
    completed_steps = await WorkflowStateManager.get_completed_steps(project_id)
    all_phases_done = all(phase in completed_steps for phase in phases)
    
    if all_phases_done:
        log("ARBORMIND", "🐳 All phases complete - Initializing sandbox for preview...")
        
        try:
            from app.sandbox import get_sandbox
            from app.orchestration.utils import broadcast_to_project
            
            sandbox = get_sandbox()
            
            # Step 1: Create sandbox
            create_result = await sandbox.create_sandbox(project_id, project_path)
            if not create_result.get("success"):
                log("ARBORMIND", f"⚠️ Sandbox creation failed: {create_result.get('error')}")
            else:
                log("ARBORMIND", "✅ Sandbox created")
                
                # Step 2: Start sandbox (will build and run containers)
                start_result = await sandbox.start_sandbox(project_id, wait_healthy=True)
                if not start_result.get("success"):
                    log("ARBORMIND", f"⚠️ Sandbox start failed: {start_result.get('error')}")
                    # Log full stderr for debugging
                    stderr = start_result.get("stderr", "")
                    if stderr:
                        log("ARBORMIND", f"📋 Docker stderr:\n{stderr[:2000]}")

                else:
                    log("ARBORMIND", "✅ Sandbox started and healthy")
                    
                    # Step 3: Get preview URL and broadcast to frontend
                    preview_url = await sandbox.get_preview_url(project_id)
                    if preview_url:
                        log("ARBORMIND", f"🔗 Preview available: {preview_url}")
                        
                        # Broadcast to frontend
                        if manager:
                            await broadcast_to_project(
                                manager,
                                project_id,
                                {
                                    "type": "PREVIEW_READY",
                                    "previewUrl": preview_url,
                                    "url": preview_url,
                                    "status": "ready",
                                }
                            )
                    else:
                        log("ARBORMIND", "⚠️ Could not determine preview URL")
                        
        except Exception as e:
            log("ARBORMIND", f"⚠️ Sandbox initialization failed: {e}")
            import traceback
            traceback.print_exc()
    
    await WorkflowStateManager.stop_workflow(project_id)




def _collect_evidence_contracts(project_path: Path) -> str:
    """Consolidate architecture files into a single string for downstream agents."""
    arch_dir = project_path / "architecture"
    if not arch_dir.exists():
        return ""
    
    parts = []
    # Order matters for context consistency
    canonical_files = ["overview.md", "frontend.md", "backend.md", "system.md", "invariants.md"]
    
    for filename in canonical_files:
        arch_file = arch_dir / filename
        if arch_file.exists():
            try:
                content = arch_file.read_text(encoding="utf-8")
                parts.append(f"### {filename}\n\n{content}")
            except Exception:
                pass
    
    # Also grab anything else in the dir just in case
    for arch_file in arch_dir.glob("*.md"):
        if arch_file.name not in canonical_files:
            try:
                content = arch_file.read_text(encoding="utf-8")
                parts.append(f"### {arch_file.name}\n\n{content}")
            except Exception:
                pass
                
    return "\n\n".join(parts)


def _collect_phase_artifacts(project_path: Path, phase: str) -> List[Path]:
    """Collect file paths for artifacts generated by a phase."""
    artifacts = []
    
    if phase == "architecture":
        arch_dir = project_path / "architecture"
        if arch_dir.exists():
            artifacts.extend(arch_dir.glob("*.md"))
    
    elif phase == "backend_models":
        models_file = project_path / "backend" / "app" / "models.py"
        if models_file.exists():
            artifacts.append(models_file)
    
    elif phase == "backend_routers":
        routers_dir = project_path / "backend" / "app" / "routers"
        if routers_dir.exists():
            artifacts.extend(routers_dir.glob("*.py"))
    
    elif phase == "frontend_mock":
        # Check common frontend locations
        for subdir in ["pages", "components", "src/pages", "src/components"]:
            frontend_dir = project_path / "frontend" / subdir
            if frontend_dir.exists():
                artifacts.extend(frontend_dir.glob("*.jsx"))
                artifacts.extend(frontend_dir.glob("*.tsx"))
    
    elif phase == "system_integration":
        main_file = project_path / "backend" / "app" / "main.py"
        if main_file.exists():
            artifacts.append(main_file)
    
    elif phase == "backend_testing":
        # Collect backend test files
        tests_dir = project_path / "backend" / "tests"
        if tests_dir.exists():
            artifacts.extend(tests_dir.glob("test_*.py"))
            artifacts.extend(tests_dir.glob("*_test.py"))
    
    elif phase == "frontend_testing":
        # Collect frontend test files
        for test_dir in ["tests", "e2e", "__tests__"]:
            frontend_tests = project_path / "frontend" / test_dir
            if frontend_tests.exists():
                artifacts.extend(frontend_tests.glob("*.spec.ts"))
                artifacts.extend(frontend_tests.glob("*.spec.js"))
                artifacts.extend(frontend_tests.glob("*.test.ts"))
                artifacts.extend(frontend_tests.glob("*.test.js"))
    
    return list(artifacts)[:10]  # Limit to 10 files



# Legacy alias - will be removed
run_fast_v2_workflow = run_arbormind_workflow

