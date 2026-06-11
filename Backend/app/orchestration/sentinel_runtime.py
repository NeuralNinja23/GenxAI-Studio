# app/orchestration/sentinel_runtime.py
"""
V4 Orchestration — Stage 6: Minimal Cognition

Implements the Cognitive Branch Controller exploring candidate universes
and executing deterministic cycles via the Immutable Execution Kernel.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import uuid
import time
import asyncio

from app.core.logging import log
from app.sentinel.directives import IntentField
from app.models.runtime_models import (
    MutationTier,
    RepairScope,
    RepairIntent,
)
from app.sentinel.topology.project_graph import ProjectTopologyGraph
from app.sentinel.topology.node_types import NodeType
from app.sentinel.topology.topology_version_manager import (
    TopologyVersionManager,
    TopologyVersionRecord,
)

from app.sentinel.cognition.sentinel_core import SentinelCore
from app.sentinel.cognition.patch_ir import PatchIR
# MutationEngine is imported locally where needed from app.studio.mutation.mutation_engine

from app.studio.faculties.victoria import VictoriaUIFaculty
from app.studio.faculties.derek import DerekAPIFaculty
from app.studio.faculties.luna import LunaSchemaFaculty
from app.studio.faculties.reggie import ReggieWorkflowFaculty

from app.sentinel.runtime.execution_kernel import (
    get_kernel,
    ProjectionCycleContext,
)

from app.sentinel.validation.validation_bus import ValidationBus
from app.sentinel.validation.validation_logger import ValidationLogger
from app.sentinel.failure_memory.memory_access_layer import MemoryAccessLayer
from app.sentinel.failure_memory.failure_geometry import FailureGeometry
from app.sentinel.cognition.intent_parser import IntentParser
from app.sentinel.topology.ast_generator import ASTGenerator

from app.sentinel.routing import (
    FailureClassifier,
    FailureDomain,
    RoutingDecision,
    TerminalStatus,
    SearchOutcome,
    AtlasFailureReason,
)
from app.sentinel.config.oracle_policy import OraclePolicyLoader, compute_oracle


class SentinelRuntime:
    """
    Cognitive Branch Explorer Controller.

    Drives parallel branch generation, convergence checks,
    and synchronous kernel commits through a 10-phase recursive recovery loop.
    """

    def __init__(self, max_branches: int = 5):
        self.sentinel_core = SentinelCore(max_branches)
        
        # Load oracle policy from oracle_policy.json
        policy_path = Path(__file__).resolve().parent.parent / "sentinel" / "config" / "oracle_policy.json"
        self._oracle_policy = OraclePolicyLoader.load(policy_path)

    async def explore_and_project(
        self,
        project_id: str,
        project_path: Path,
        user_request: str,
    ) -> bool:
        """
        Drives the 10-phase exploration and projection loop.
        """
        log("SENTINEL_RUNTIME", f"🧠 Initiating Stage 6 exploration cycle for: {project_id}")
        
        # Phase 10 Prep: Clear the Validation Bus at the start of the E2E cycle.
        ValidationBus().clear()
        
        # ─────────────────────────────────────────────
        # Fetch Intent Boundary
        # ─────────────────────────────────────────────
        intent = await IntentField.find_one({"project_id": project_id})
        if not intent:
            log("SENTINEL_RUNTIME", f"🌱 Initializing seed IntentField for {project_id}")
            intent = IntentField(project_id=project_id, original_request=user_request)
            await intent.insert()
            
        intent = await IntentParser.parse_and_anchor_intent(user_request, intent)
        await intent.save()

        # ─────────────────────────────────────────────
        # Fetch Baseline Topology Graph
        # ─────────────────────────────────────────────
        current_graph = await TopologyVersionManager.get_active_topology(project_id)
        if not current_graph:
            log("SENTINEL_RUNTIME", "💡 Scaffolding initial baseline topology.")
            current_graph = ProjectTopologyGraph(project_id=project_id)
            root_ui_id = f"root_ui_{uuid.uuid4().hex[:6]}"
            current_graph.add_node(
                node_id=root_ui_id,
                node_type=NodeType.UI_NODE,
                properties={"component_name": "Dashboard", "generated": True, "is_root": True}
            )
            state_node_id = f"{root_ui_id}_state"
            current_graph.add_node(
                node_id=state_node_id,
                node_type=NodeType.STATE_NODE,
                properties={"generated": True, "scope": root_ui_id}
            )
            current_graph.add_edge(source_id=root_ui_id, target_id=state_node_id, relation="binds_state")
            await TopologyVersionManager.commit_topology(project_id, current_graph, author="kernel")

        # ─────────────────────────────────────────────
        # Main Recursive Repair Loop (Phases 1-9)
        # ─────────────────────────────────────────────
        kernel = get_kernel()
        mal = MemoryAccessLayer()
        MAX_REPAIRS = 3
        final_success = False
        
        # Repair State Variables
        repair_intent = None
        oracle_before = None
        current_repair_scope = None
        consecutive_repair_failures = 0
        active_run_cycles = []

        # Phase 3 Routing telemetry variables
        primary_failure_category = None
        active_failure_categories = []
        routing_decision = None
        routing_reason = None
        search_outcome = SearchOutcome.NOT_RUN.value
        
        for attempt in range(MAX_REPAIRS):
            log("SENTINEL_RUNTIME", f"🔄 E2E Cycle Attempt {attempt+1}/{MAX_REPAIRS}")
            
            # Determine Mutation Tier for Context
            max_tier = MutationTier.COSMETIC
            for node in current_graph.nodes.values():
                tier_val = MutationTier.BEHAVIORAL
                if node.node_type == NodeType.UI_NODE:
                    tier_val = MutationTier.STRUCTURAL_UI
                elif node.node_type in [NodeType.API_NODE, NodeType.ROUTE_NODE, NodeType.SCHEMA_NODE]:
                    tier_val = MutationTier.TOPOLOGY
                if tier_val.value > max_tier.value:
                    max_tier = tier_val
                    
            ast_files = ASTGenerator.generate(current_graph)
            proposed_writes = list(ast_files.keys()) or ["Frontend/src/components/Placeholder.tsx"]
            
            ctx = ProjectionCycleContext(
                project_id=project_id,
                project_path=project_path,
                mutation_tier=max_tier,
                proposed_writes=proposed_writes,
                required_oracle_tiers=["syntax_oracle", "topology_oracle", "behavioral_oracle", "runtime_oracle"]
            )
            
            # Forward repair state and telemetry to context
            ctx.repair_intent = repair_intent
            ctx.oracle_before = oracle_before
            if current_repair_scope is None:
                current_repair_scope = RepairScope.COMPONENT
            ctx.current_repair_scope = current_repair_scope
            ctx.consecutive_repair_failures = consecutive_repair_failures

            ctx.primary_failure_category = primary_failure_category
            ctx.active_failure_categories = active_failure_categories
            ctx.routing_decision = routing_decision
            ctx.routing_reason = routing_reason
            ctx.search_outcome = search_outcome
            
            # Phases 1-3: Projection Generation, Verification, Failure Analysis
            result = await kernel.run_projection_cycle(
                ctx=ctx,
                graph=current_graph,
                llm_client=kernel.llm_client,
                oracle_policy=self._oracle_policy
            )
            success = result.get("success", False)
            verification = result.get("verification")
            
            if success:
                log("SENTINEL_RUNTIME", "✅ Projection cycle verified successfully!")
                # Phase 5 (Commit): Promote candidate memory to committed
                mal.commit_memory(project_id)
                final_success = True
                break
                
            # If we reach here, Verification Failed.
            log("SENTINEL_RUNTIME", "❌ Verification failed. Entering Failure Analysis and Governance...")
            failures = getattr(verification, "failures", []) if verification else []
            
            # Phase 5: Candidate Memory Update
            log("SENTINEL_RUNTIME", "💾 Writing Candidate Memory for repair loop...")
            fg = FailureGeometry()
            total_nodes = len(current_graph.nodes)
            ui_count = sum(1 for n in current_graph.nodes.values() if n.node_type == NodeType.UI_NODE)
            
            for fail in failures:
                vector = fg.encode_failure(
                    node_count=total_nodes,
                    error_class=fail.failure_type,
                    ui_node_count=ui_count
                )
                # Insert as candidate
                mal.insert_failure_record(
                    failure_id=f"verif_fail_{uuid.uuid4().hex[:6]}",
                    vector=vector,
                    error_class=fail.failure_type,
                    cycle_id=project_id,
                    details=fail.details,
                    verification_stage=fail.stage,
                    status="candidate"
                )
                
            # 1. Classify failures
            profile = FailureClassifier.classify(failures)
            active_domains = {profile.primary} | profile.secondary

            # 2. Determine routing decision
            route, route_reason = self._route_for_profile(profile)
            routing_decision = route.value
            routing_reason = route_reason
            primary_failure_category = profile.primary_category.value
            active_failure_categories = [c.value for c in profile.active_categories]
            
            # Update current context so that its record_projection_run logs correct values
            ctx.routing_decision = routing_decision
            ctx.routing_reason = routing_reason
            ctx.primary_failure_category = primary_failure_category
            ctx.active_failure_categories = active_failure_categories

            # 3. Log the [ROUTING] line (exact format from spec)
            log("ROUTING", f"domains={sorted(d.value for d in active_domains)} primary={profile.primary.value} route={route.value}")

            # 4. Execute one path
            active_branches = []
            topology_search_executed = False
            best_branch = None
            selected_branch = None

            if route == RoutingDecision.INFRASTRUCTURE:
                await kernel.rollback_cycle(ctx, "Rollback staged failed projection on INFRASTRUCTURE route")
                terminal_status = TerminalStatus.INFRASTRUCTURE_ABORT
                final_success = False
                break

            elif route == RoutingDecision.ATLAS:
                if self._oracle_policy is not None and failures:
                    oracle_before = compute_oracle(failures, self._oracle_policy)
                else:
                    oracle_before = 1.0

                # Atlas reads from .genx_staging so it sees the failed files before rollback
                staging_project_path = project_path / ".genx_staging"
                repair_intent, reason_code, status_code = await self._run_atlas_with_reason(
                    failures=failures,
                    current_graph=current_graph,
                    max_tier=max_tier,
                    active_goals=intent.expected_contracts if hasattr(intent, "expected_contracts") else [],
                    oracle_before=oracle_before,
                    current_repair_scope=ctx.current_repair_scope,
                    kernel_llm_client=kernel.llm_client,
                    project_path=staging_project_path
                )
                
                # Now perform the deferred rollback
                await kernel.rollback_cycle(ctx, "Rollback staged failed projection after Atlas repair context generation")
                
                search_outcome = SearchOutcome.NOT_RUN.value
                ctx.search_outcome = search_outcome

                if reason_code is not None:
                    # Atlas failed — abort E2E per spec
                    routing_reason = f"{route_reason}; atlas:{reason_code.value}"
                    ctx.routing_reason = routing_reason
                    # Map to the corresponding TerminalStatus
                    terminal_status = status_code
                    final_success = False
                    break
                elif repair_intent is None:
                    # Atlas returned None — unrepairable
                    routing_reason = f"{route_reason}; atlas:unrepairable"
                    ctx.routing_reason = routing_reason
                    terminal_status = TerminalStatus.UNREPAIRABLE_CODE_FAILURE
                    final_success = False
                    break

                # Atlas succeeded — set on loop variable for NEXT cycle's projection context
                ctx._repair_failures = list(failures)
                
                # Update current_repair_scope and consecutive_repair_failures from context
                current_repair_scope = ctx.current_repair_scope
                consecutive_repair_failures = ctx.consecutive_repair_failures

            elif route == RoutingDecision.TOPOLOGY:
                # Rollback staged projection before initiating branch mutations
                await kernel.rollback_cycle(ctx, "Rollback staged failed projection on TOPOLOGY route before branch generation")
                topology_search_executed = True
                root_branch = self.sentinel_core.initialize_root(current_graph)
                repair_intent_context = f"ORIGINAL INTENT: {user_request}"
                
                proposals = []
                proposals.extend(await VictoriaUIFaculty.propose_mutations(root_branch, repair_intent_context, intent))
                proposals.extend(await DerekAPIFaculty.propose_mutations(root_branch, repair_intent_context, intent))
                proposals.extend(await LunaSchemaFaculty.propose_mutations(root_branch, repair_intent_context, intent))
                proposals.extend(await ReggieWorkflowFaculty.propose_mutations(root_branch, repair_intent_context, intent))
 
                active_branches = self.sentinel_core.explore_possibilities(
                    intent, proposals
                )

                # S-0.7 Pre-Projection Regression Gates helper
                from app.sentinel.verification.verification_gate import SentinelTopologyVerifier
                
                def detect_pre_projection_regressions(parent_graph: ProjectTopologyGraph, child_graph: ProjectTopologyGraph) -> List[str]:
                    regressions = []
                    # 1. Router removed check
                    parent_has_router = any(n.properties.get("is_root") for n in parent_graph.nodes.values())
                    child_has_router = any(n.properties.get("is_root") for n in child_graph.nodes.values())
                    if parent_has_router and not child_has_router:
                        regressions.append("router_removed")
                    # 2. Failure count check
                    parent_fails = len(SentinelTopologyVerifier.verify(parent_graph).failures)
                    child_fails = len(SentinelTopologyVerifier.verify(child_graph).failures)
                    if child_fails > parent_fails:
                        regressions.append("in_memory_failures_increased")
                    return regressions

                if not active_branches:
                    search_outcome = SearchOutcome.NO_CANDIDATES.value
                    ctx.search_outcome = search_outcome
                    log("SENTINEL_RUNTIME", "❌ No stable repair branches could be generated. Exiting.")
                    break
                else:
                    for branch in active_branches:
                        branch.is_stable = True

                    # Select best branch with regression check
                    selected_branch = None
                    for branch in active_branches:
                        regressions = detect_pre_projection_regressions(current_graph, branch.topology_graph)
                        if not regressions:
                            selected_branch = branch
                            break
                        else:
                            log("SENTINEL_RUNTIME", f"⚠️ Regression Gate S-0.7 Rejected branch {branch.branch_id[:8]}: {regressions}")
                            parent_failures = SentinelTopologyVerifier.verify(current_graph).failures
                            child_failures = SentinelTopologyVerifier.verify(branch.topology_graph).failures
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
                            log("SENTINEL_RUNTIME", (
                                f"[REGRESSION_DIAGNOSTICS]\n"
                                f"branch_id={branch.branch_id}\n"
                                f"parent_failures={len(parent_failures)}\n"
                                f"child_failures={len(child_failures)}\n"
                                f"delta={len(child_failures) - len(parent_failures)}\n\n"
                                f"resolved_failures={list(resolved)}\n\n"
                                f"introduced_failures={list(introduced)}"
                            ))

                    if not selected_branch:
                        log("SENTINEL_RUNTIME", "⚠️ All mutated branches regressed. Falling back to parent/root.")
                        selected_branch = root_branch

                    best_branch = selected_branch
                    search_outcome = (
                        SearchOutcome.CANDIDATE_SELECTED.value
                        if best_branch is not root_branch
                        else SearchOutcome.CANDIDATES_GENERATED.value
                    )
                    ctx.search_outcome = search_outcome

                    log("SENTINEL_RUNTIME", f"🏆 Selected repair branch: {best_branch.branch_id}")
                    await TopologyVersionManager.commit_topology(
                        project_id=project_id,
                        graph=best_branch.topology_graph,
                        branch_name=f"repair_{attempt}",
                        author="cognition",
                        metadata={"branch_id": best_branch.branch_id}
                    )
                    current_graph = best_branch.topology_graph

                    # S-0.9 Omega termination check
                    from app.sentinel.cognition.convergence_engine import ConvergenceEngine
                    converged = ConvergenceEngine.is_converged(best_branch.entropy_history)
                    no_improvement = (selected_branch == root_branch or selected_branch is None)
                    omega_check = converged and no_improvement
                    if omega_check:
                        log("SENTINEL_RUNTIME", f"🚪 Omega convergence trigger met: Converged(H)={converged}, NoValidImprovementExists={no_improvement}. Terminating E2E repair loop.")
                        break

                    # Stagnant(H) check
                    stagnant = ConvergenceEngine.is_stagnant(best_branch.entropy_history)
                    if stagnant:
                        log("SENTINEL_RUNTIME", "⚠️ Stagnant state detected (Impasse). Proposing escape mutations.")
                        from app.studio.mutation.mutation_engine import MutationEngine
                        escape_proposals = MutationEngine.propose_escape_mutations(best_branch, "IMPASSE", {"details": "Stagnant entropy history"})
                        if escape_proposals:
                            log("SENTINEL_RUNTIME", f"✨ Injected {len(escape_proposals)} escape mutations to resolve impasse.")
                            self.sentinel_core.explore_possibilities(intent, escape_proposals)

            else:
                await kernel.rollback_cycle(ctx, "Rollback staged failed projection on UNKNOWN route")
                search_outcome = SearchOutcome.NOT_RUN.value
                log("SENTINEL_RUNTIME", f"⚠️ Route UNKNOWN, terminating loop.")
                break

            ctx.search_outcome = search_outcome

            # 5. Explicit route-state assertions (per spec)
            if route == RoutingDecision.ATLAS:
                assert repair_intent is not None, "ATLAS route requires repair_intent"
                assert len(active_branches) == 0, "ATLAS route must not run topology search"
            elif route == RoutingDecision.TOPOLOGY:
                assert repair_intent is None, "TOPOLOGY route must not run Atlas repair"
                assert topology_search_executed, "TOPOLOGY route must execute topology search"
            elif route == RoutingDecision.INFRASTRUCTURE:
                assert repair_intent is None, "INFRASTRUCTURE route must not run Atlas repair"
                assert len(active_branches) == 0, "INFRASTRUCTURE route must not run topology search"

        # Phase 9: Final Decision
        if final_success:
            log("SENTINEL_RUNTIME", f"🎉 E2E Flow Completed Successfully for {project_id}")
        else:
            log("SENTINEL_RUNTIME", f"💀 E2E Flow Exhausted. Final result: GATE_REJECT")
            
        # Cleanup staging directory at the end of E2E flow
        staging_path = project_path / ".genx_staging"
        if staging_path.exists():
            try:
                import shutil
                shutil.rmtree(staging_path)
            except Exception as cleanup_err:
                log("SENTINEL_RUNTIME", f"⚠️ Failed to clean up staging directory: {cleanup_err}")

        # Phase 10: Telemetry Flush
        run_id = str(uuid.uuid4())
        events = ValidationBus().get_events()
        log("SENTINEL_RUNTIME", f"📊 Flushing {len(events)} telemetry events to ValidationLogger...")
        ValidationLogger.flush_events(run_id, events)
        
        return final_success

    @staticmethod
    def _route_for_profile(profile) -> tuple[RoutingDecision, str]:
        """Spec priority: INFRASTRUCTURE > ATLAS > UNKNOWN."""
        active_domains = {profile.primary} | profile.secondary
        if FailureDomain.INFRASTRUCTURE in active_domains:
            return RoutingDecision.INFRASTRUCTURE, f"domain:INFRASTRUCTURE present (cats={profile.severity_score:.0f})"
        
        # Route all non-infrastructure failures to ATLAS (CODE, TOPOLOGY, etc.)
        non_infra_domains = active_domains - {FailureDomain.INFRASTRUCTURE}
        if non_infra_domains:
            domains_str = "/".join(sorted(d.value for d in non_infra_domains))
            return RoutingDecision.ATLAS, f"domain:{domains_str} present (primary_cat={profile.primary_category.value})"
            
        return RoutingDecision.UNKNOWN, "no domain classified"

    async def _run_atlas_with_reason(
        self,
        failures,
        current_graph,
        max_tier,
        active_goals,
        oracle_before,
        current_repair_scope,
        kernel_llm_client,
        project_path=None
    ) -> tuple[Any, Optional[AtlasFailureReason], Optional[TerminalStatus]]:
        """Wrap AtlasFaculty.propose_repair_intent with explicit reason codes."""
        try:
            from app.sentinel.failure_memory.failure_geometry import FailureGeometry
            from app.studio.faculties.atlas_faculty import AtlasFaculty
            
            state_vector = FailureGeometry().encode_state(
                failures=failures,
                graph=current_graph,
                mutation_tier=max_tier.value if hasattr(max_tier, 'value') else max_tier
            )
            repair_context = AtlasFaculty.build_repair_context(
                failures=failures,
                state_fingerprint=state_vector,
                goals=active_goals,
                oracle_before=oracle_before,
                workspace_root=project_path
            )
            
            # Print Atlas diagnostic block
            print(f"[ATLAS]\nRepair Context:\nfiles={len(repair_context.affected_files)}\noracle_before={oracle_before}\nscope={current_repair_scope.name}")
            
            intent = await asyncio.wait_for(
                AtlasFaculty.propose_repair_intent(
                    context=repair_context,
                    llm_client=kernel_llm_client,
                ),
                timeout=120.0
            )
        except asyncio.TimeoutError:
            return None, AtlasFailureReason.TIMEOUT, TerminalStatus.ATLAS_UNAVAILABLE
        except Exception as e:
            log("SENTINEL_RUNTIME", f"Exception during Atlas repair: {e}")
            return None, AtlasFailureReason.EXCEPTION, TerminalStatus.ATLAS_UNAVAILABLE
            
        if intent is None:
            return None, AtlasFailureReason.EMPTY_RESPONSE, TerminalStatus.ATLAS_UNAVAILABLE
        return intent, None, None


