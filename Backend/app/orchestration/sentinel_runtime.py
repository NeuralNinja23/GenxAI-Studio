# app/orchestration/sentinel_runtime.py
"""
V4 Orchestration — Stage 6: Minimal Cognition

Implements the Cognitive Branch Controller exploring candidate universes
and executing deterministic cycles via the Immutable Execution Kernel.
"""

from pathlib import Path
from typing import List
import uuid

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


class SentinelRuntime:
    """
    Cognitive Branch Explorer Controller.

    Drives parallel branch generation, convergence checks,
    and synchronous kernel commits.
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
        Drives the exploration and projection loop.

        Non-linear branch search happens in cognition,
        followed by deterministic execution.
        """

        log(
            "SENTINEL_RUNTIME",
            f"🧠 Initiating Stage 6 exploration cycle for: {project_id}"
        )

        # ─────────────────────────────────────────────
        # 1. Fetch Intent Boundary
        # ─────────────────────────────────────────────

        intent = await IntentField.find_one({
            "project_id": project_id
        })

        if not intent:

            log(
                "SENTINEL_RUNTIME",
                f"🌱 New project detected. Initializing rich seed IntentField bounds for {project_id}"
            )

            intent = IntentField(
                project_id=project_id,
                original_request=user_request
            )

            await intent.insert()

        # Phase 5: Semantic Salience Mapping & Anchoring
        from app.sentinel.cognition.intent_parser import IntentParser
        intent = await IntentParser.parse_and_anchor_intent(user_request, intent)
        await intent.save()


        # ─────────────────────────────────────────────
        # 2. Fetch Baseline Topology Graph
        # ─────────────────────────────────────────────

        baseline_graph = await TopologyVersionManager.get_active_topology(
            project_id
        )

        if not baseline_graph:

            log(
                "SENTINEL_RUNTIME",
                "💡 Active Topology Graph not found. "
                "Scaffolding initial baseline."
            )

            baseline_graph = ProjectTopologyGraph(
                project_id=project_id
            )

            # ─────────────────────────────────────────
            # Create emergent root UI node (Dashboard instead of RootView)
            # ─────────────────────────────────────────

            root_ui_id = f"root_ui_{uuid.uuid4().hex[:6]}"

            baseline_graph.add_node(
                node_id=root_ui_id,
                node_type=NodeType.UI_NODE,
                properties={
                    "component_name": "Dashboard",
                    "generated": True,
                    "is_root": True,
                }
            )

            # ─────────────────────────────────────────
            # Create causal grounding state node
            # ─────────────────────────────────────────

            state_node_id = f"{root_ui_id}_state"

            baseline_graph.add_node(
                node_id=state_node_id,
                node_type=NodeType.STATE_NODE,
                properties={
                    "generated": True,
                    "scope": root_ui_id,
                }
            )

            # ─────────────────────────────────────────
            # Bind UI -> State
            # ─────────────────────────────────────────

            baseline_graph.add_edge(
                source_id=root_ui_id,
                target_id=state_node_id,
                relation="binds_state",
            )

            # Persist baseline topology
            await TopologyVersionManager.commit_topology(
                project_id=project_id,
                graph=baseline_graph,
                author="kernel",
            )

        # ─────────────────────────────────────────────
        # 3. Initialize Root Branch
        # ─────────────────────────────────────────────

        root_branch = self.sentinel_core.initialize_root(
            baseline_graph
        )

        # ─────────────────────────────────────────────
        # 4. Faculty Mutation Proposals
        # ─────────────────────────────────────────────

        log(
            "SENTINEL_RUNTIME",
            "🧙 Calling faculties to propose topological patches..."
        )

        proposals: List[PatchIR] = []
        proposals.extend(
            await VictoriaUIFaculty.propose_mutations(
                root_branch,
                user_request,
                intent,
            )
        )

        proposals.extend(
            await DerekAPIFaculty.propose_mutations(
                root_branch,
                user_request,
                intent,
            )
        )

        proposals.extend(
            await LunaSchemaFaculty.propose_mutations(
                root_branch,
                user_request,
                intent,
            )
        )

        proposals.extend(
            await ReggieWorkflowFaculty.propose_mutations(
                root_branch,
                user_request,
                intent,
            )
        )

        # ─────────────────────────────────────────────
        # 5. Explore Candidate Branches (Laws of Physics & Repulsion)
        # ─────────────────────────────────────────────

        log(
            "SENTINEL_RUNTIME",
            "🔀 Exploring candidate branches and filtering physics..."
        )

        active_branches = self.sentinel_core.explore_possibilities(
            intent,
            proposals,
            marcus_advisory_modifiers=None,
        )

        if not active_branches:

            log(
                "SENTINEL_RUNTIME",
                "❌ All proposed branches were blocked by "
                "ConstraintEngine or Failure Repulsion."
            )

            return False

        # ─────────────────────────────────────────────
        # 6. Resilient Parallel Marcus Governance Advisory
        # ─────────────────────────────────────────────

        log(
            "SENTINEL_RUNTIME",
            f"🧙 Conducting parallel topology governance checks on {len(active_branches)} active branches..."
        )

        import asyncio
        from datetime import datetime, timezone
        from app.sentinel.cognition.branch import BranchState

        async def evaluate_branch(branch: BranchState) -> None:
            try:
                analysis = await MarcusGovernanceAnalyst.analyze_governance(branch)
                # Store rich governance metadata inside BranchState (Strictly Advisory, No edits/writes)
                branch.governance = {
                    "modifier": float(analysis.get("marcus_advisory_modifier", 1.0)),
                    "warnings": analysis.get("warnings", []),
                    "stability": bool(analysis.get("is_stable", True)),
                    "entropy_risk": float(branch.entropy_history[-1]) if branch.entropy_history else 0.0,
                    "repulsion_score": float(branch.repulsion_score),
                    "constraint_pressure": 1.0 if branch.repulsion_score > 0.5 else 0.0,
                    "evaluated_at": datetime.now(timezone.utc).isoformat(),
                    "governance_version": "v4"
                }
            except Exception as e:
                log("SENTINEL_RUNTIME", f"⚠️ Marcus resilient degradation on branch {branch.branch_id}: {e}")
                # Catch exception and fall back to baseline/deterministic governance values (Resilient Degradation)
                branch.governance = {
                    "modifier": 1.0,
                    "warnings": [f"Governance degradation: {e}"],
                    "stability": True,
                    "entropy_risk": float(branch.entropy_history[-1]) if branch.entropy_history else 0.0,
                    "repulsion_score": float(branch.repulsion_score),
                    "constraint_pressure": 0.0,
                    "evaluated_at": datetime.now(timezone.utc).isoformat(),
                    "governance_version": "v4"
                }

        # Concurrently evaluate surviving realized branches (return_exceptions=True prevents global collapse)
        eval_tasks = [evaluate_branch(b) for b in active_branches]
        await asyncio.gather(*eval_tasks, return_exceptions=True)

        # Re-score and re-sort active branches based on the new Marcus modifiers in branch.governance
        self.sentinel_core.attention_router.route_attention(active_branches)

        # Prioritize the 'composite' branch (containing all valid faculty mutations) first to guarantee a fully compiled application,
        # followed by other non-root branches, and finally the baseline root branch.
        composite_branch = next((b for b in active_branches if b.branch_id == "composite"), None)
        non_root_branches = [b for b in active_branches if b.branch_id != "root"]
        best_branch = composite_branch if composite_branch else (non_root_branches[0] if non_root_branches else active_branches[0])


        log(
            "SENTINEL_RUNTIME",
            f"👑 Selected best candidate branch: "
            f"{best_branch.branch_id} "
            f"(weight={best_branch.attention_weight:.2f}, "
            f"entropy={best_branch.entropy_history[-1]:.4f})"
        )

        if getattr(best_branch, "needs_stabilization", False):
            log("SENTINEL_RUNTIME", "⚠️ Best candidate branch requires stabilization due to SOFT constraint violations. Invoking MutationEngine.")
            escape_patches = MutationEngine.propose_escape_mutations(
                branch=best_branch,
                trigger_reason="STAGNATION"
            )
            if escape_patches:
                stabilized_branch = self.sentinel_core.tree_manager.spawn_branch(best_branch, None)
                for patch in escape_patches:
                    stabilized_branch = self.sentinel_core.tree_manager.spawn_branch(stabilized_branch, patch)
                best_branch = stabilized_branch
                log("SENTINEL_RUNTIME", f"✅ Branch stabilized. New active branch: {best_branch.branch_id}")

        # ─────────────────────────────────────────────
        # 7. Persist Candidate Topology
        # ─────────────────────────────────────────────

        await TopologyVersionManager.commit_topology(
            project_id=project_id,
            graph=best_branch.topology_graph,
            branch_name="main",
            author="cognition",
            metadata={
                "branch_id": best_branch.branch_id
            }
        )

        # ─────────────────────────────────────────────
        # 8. Build Projection Context
        # ─────────────────────────────────────────────

        max_tier = MutationTier.COSMETIC

        for node in best_branch.topology_graph.nodes.values():

            tier_val = MutationTier.BEHAVIORAL

            if node.node_type == NodeType.UI_NODE:
                tier_val = MutationTier.STRUCTURAL_UI

            elif node.node_type in [
                NodeType.API_NODE,
                NodeType.ROUTE_NODE,
                NodeType.SCHEMA_NODE,
            ]:
                tier_val = MutationTier.TOPOLOGY

            if tier_val.value > max_tier.value:
                max_tier = tier_val

        from app.sentinel.topology.ast_generator import ASTGenerator

        ast_files = ASTGenerator.generate(
            best_branch.topology_graph
        )

        proposed_writes = list(ast_files.keys())

        if not proposed_writes:
            proposed_writes = [
                "Frontend/src/components/Placeholder.tsx"
            ]

        oracle_tiers = []

        if max_tier == MutationTier.COSMETIC:
            oracle_tiers = ["syntax_oracle"]

        elif max_tier == MutationTier.STRUCTURAL_UI:
            oracle_tiers = [
                "syntax_oracle",
                "topology_oracle",
            ]

        elif max_tier == MutationTier.BEHAVIORAL:
            oracle_tiers = [
                "syntax_oracle",
                "topology_oracle",
                "behavioral_oracle",
            ]

        elif max_tier == MutationTier.TOPOLOGY:
            oracle_tiers = [
                "syntax_oracle",
                "topology_oracle",
                "behavioral_oracle",
                "runtime_oracle",
            ]

        ctx = ProjectionCycleContext(
            project_id=project_id,
            project_path=project_path,
            mutation_tier=max_tier,
            proposed_writes=proposed_writes,
            required_oracle_tiers=oracle_tiers,
        )

        # ─────────────────────────────────────────────
        # 9. Execute Projection Cycle
        # ─────────────────────────────────────────────

        log(
            "SENTINEL_RUNTIME",
            "⚡ Executing synchronous Projection Cycle..."
        )

        kernel = get_kernel()

        success = await kernel.run_projection_cycle(ctx)

        # ─────────────────────────────────────────────
        # 10. Success Path
        # ─────────────────────────────────────────────

        if success:

            log(
                "SENTINEL_RUNTIME",
                "✅ Candidate branch successfully "
                "project-committed and verified!"
            )

            best_branch.is_committed = True

            return True

        # ─────────────────────────────────────────────
        # 11. Failure Path
        # ─────────────────────────────────────────────

        log(
            "SENTINEL_RUNTIME",
            "❌ Projection cycle failed / "
            "Oracles blocked transaction. "
            "Registering failure in SQLite."
        )

        failed_record = await TopologyVersionRecord.find_one(
            {
                "project_id": project_id,
                "branch_name": "main",
            },
            sort=[("created_at", -1)],
        )

        if failed_record:

            await failed_record.delete()

            log(
                "SENTINEL_RUNTIME",
                "🗑️ Reverted failed candidate topology "
                "record from database."
            )

        # ─────────────────────────────────────────────
        # 12. Escape Mutation Path
        # ─────────────────────────────────────────────

        log(
            "SENTINEL_RUNTIME",
            "🔄 Spawning event-driven mutation escape path..."
        )

        escape_patches = MutationEngine.propose_escape_mutations(
            best_branch,
            trigger_reason="ORACLE_BLOCK",
            oracle_feedback={
                "failed_oracles": [
                    {
                        "name": "runtime",
                        "message": (
                            "Transaction failed or "
                            "oracles blocked"
                        ),
                    }
                ]
            },
        )

        escape_active = self.sentinel_core.explore_possibilities(
            intent,
            escape_patches,
            marcus_advisory_modifiers=None,
        )

        if escape_active:

            escape_branch = escape_active[0]

            log(
                "SENTINEL_RUNTIME",
                f"✨ Generated stable escape mutation path: "
                f"{escape_branch.branch_id}"
            )

            await TopologyVersionManager.commit_topology(
                project_id=project_id,
                graph=escape_branch.topology_graph,
                branch_name="main",
                author="cognition",
                metadata={
                    "branch_id": escape_branch.branch_id,
                    "is_escape": True,
                },
            )

        return False