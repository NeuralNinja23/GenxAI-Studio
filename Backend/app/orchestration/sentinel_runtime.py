# app/orchestration/sentinel_runtime.py
"""
V4 Orchestration — Stage 6: Minimal Cognition

Implements the Cognitive Branch Controller exploring candidate universes
and executing deterministic cycles via the Immutable Execution Kernel.
"""

from pathlib import Path
from typing import List, Dict, Any
import uuid
import time
import asyncio

from app.core.logging import log
from app.sentinel.directives import IntentField
from app.models.runtime_models import MutationTier
from app.sentinel.topology.project_graph import ProjectTopologyGraph
from app.sentinel.topology.node_types import NodeType
from app.sentinel.topology.topology_version_manager import (
    TopologyVersionManager,
    TopologyVersionRecord,
)

from app.sentinel.cognition.sentinel_core import SentinelCore
from app.sentinel.cognition.patch_ir import PatchIR
from app.sentinel.cognition.mutation_engine import MutationEngine

from app.agents.sub_agents import (
    VictoriaUIFaculty,
    DerekAPIFaculty,
    LunaSchemaFaculty,
    ReggieWorkflowFaculty,
    MarcusGovernanceAnalyst,
)

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


class SentinelRuntime:
    """
    Cognitive Branch Explorer Controller.

    Drives parallel branch generation, convergence checks,
    and synchronous kernel commits through a 10-phase recursive recovery loop.
    """

    def __init__(self, max_branches: int = 5):
        self.sentinel_core = SentinelCore(max_branches)

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
            
            # Phases 1-3: Projection Generation, Verification, Failure Analysis
            result = await kernel.run_projection_cycle(ctx=ctx, graph=current_graph, llm_client=kernel.llm_client)
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
            
            # Phase 4: Marcus Governance
            marcus_eval = await MarcusGovernanceAnalyst.evaluate_failures(failures)
            decision = marcus_eval.get("decision", "REJECT")
            repair_strategy = marcus_eval.get("repair_strategy", "")
            
            log("SENTINEL_RUNTIME", f"🧠 Marcus Decision: {decision}. Strategy: {repair_strategy}")
            
            if decision == "REJECT":
                log("SENTINEL_RUNTIME", "⛔ Marcus rejected the branch as unrecoverable. Exiting loop.")
                break
                
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
                
            # Phase 6 & 7: Universe of Thought Branching & Evaluation
            log("SENTINEL_RUNTIME", "🌌 Expanding branches via faculties for repair...")
            root_branch = self.sentinel_core.initialize_root(current_graph)
            repair_intent_context = f"REPAIR STRATEGY: {repair_strategy}\nORIGINAL INTENT: {user_request}"
            
            proposals: List[PatchIR] = []
            proposals.extend(await VictoriaUIFaculty.propose_mutations(root_branch, repair_intent_context, intent))
            proposals.extend(await DerekAPIFaculty.propose_mutations(root_branch, repair_intent_context, intent))
            proposals.extend(await LunaSchemaFaculty.propose_mutations(root_branch, repair_intent_context, intent))
            proposals.extend(await ReggieWorkflowFaculty.propose_mutations(root_branch, repair_intent_context, intent))
            
            active_branches = self.sentinel_core.explore_possibilities(
                intent, proposals, marcus_advisory_modifiers=None
            )
            
            if not active_branches:
                log("SENTINEL_RUNTIME", "❌ No stable repair branches could be generated. Exiting.")
                break
                
            governance_tasks = [
                MarcusGovernanceAnalyst.analyze_governance(branch, "CLEAN")
                for branch in active_branches
            ]
            gov_results = await asyncio.gather(*governance_tasks, return_exceptions=True)
            
            marcus_mods = {}
            for branch, res in zip(active_branches, gov_results):
                if not isinstance(res, Exception):
                    marcus_mods[branch.branch_id] = res.get("marcus_advisory_modifier", 1.0)
                else:
                    marcus_mods[branch.branch_id] = 1.0
                    
            # Phase 8: Branch Selection
            active_branches.sort(key=lambda b: (b.is_stable, marcus_mods.get(b.branch_id, 1.0), -b.repulsion_score), reverse=True)
            best_branch = active_branches[0]
            
            log("SENTINEL_RUNTIME", f"🏆 Selected repair branch: {best_branch.branch_id}")
            await TopologyVersionManager.commit_topology(
                project_id=project_id,
                graph=best_branch.topology_graph,
                branch_name=f"repair_{attempt}",
                author="cognition",
                metadata={"branch_id": best_branch.branch_id}
            )
            
            current_graph = best_branch.topology_graph

        # Phase 9: Final Decision
        if final_success:
            log("SENTINEL_RUNTIME", f"🎉 E2E Flow Completed Successfully for {project_id}")
        else:
            log("SENTINEL_RUNTIME", f"💀 E2E Flow Exhausted. Final result: GATE_REJECT")
            
        # Phase 10: Telemetry Flush
        run_id = str(uuid.uuid4())
        events = ValidationBus().get_events()
        log("SENTINEL_RUNTIME", f"📊 Flushing {len(events)} telemetry events to ValidationLogger...")
        ValidationLogger.flush_events(run_id, events)
        
        return final_success
