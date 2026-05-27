# app/orchestration/arbor_runtime.py
"""
V4 Orchestration — Stage 6: Minimal Cognition

Implements the Cognitive Branch Controller exploring candidate universes
and executing deterministic cycles via the Immutable Execution Kernel.
"""

from pathlib import Path
from typing import List
import uuid

from app.core.logging import log
from app.models.directive import IntentField
from app.models.runtime_models import MutationTier
from app.topology.project_graph import ProjectTopologyGraph
from app.topology.node_types import NodeType
from app.topology.topology_version_manager import (
    TopologyVersionManager,
    TopologyVersionRecord,
)

from app.cognition.arbor_core import ArborCore
from app.cognition.patch_ir import PatchIR
from app.cognition.mutation_engine import MutationEngine

from app.agents.sub_agents import (
    VictoriaUIFaculty,
    DerekAPIFaculty,
    LunaSchemaFaculty,
    ReggieWorkflowFaculty,
    MarcusGovernanceAnalyst,
)

from app.runtime.execution_kernel import (
    get_kernel,
    ProjectionCycleContext,
)

from app.failure_memory.failure_geometry import FailureGeometry


class ArborRuntime:
    """
    Cognitive Branch Explorer Controller.

    Drives parallel branch generation, convergence checks,
    and synchronous kernel commits.
    """

    def __init__(self, max_branches: int = 5):
        self.arbor_core = ArborCore(max_branches)
        self.failure_db = FailureGeometry()

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
            "ARBOR_RUNTIME",
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
                "ARBOR_RUNTIME",
                f"💡 Seed IntentField not found. Creating default bounds for {project_id}"
            )

            intent = IntentField(
                project_id=project_id,
                invariants=[
                    "Auth boundaries must be preserved.",
                    "No circular imports allowed.",
                ],
            )

            await intent.insert()

        # ─────────────────────────────────────────────
        # 2. Fetch Baseline Topology Graph
        # ─────────────────────────────────────────────

        baseline_graph = await TopologyVersionManager.get_active_topology(
            project_id
        )

        if not baseline_graph:

            log(
                "ARBOR_RUNTIME",
                "💡 Active Topology Graph not found. "
                "Scaffolding initial baseline."
            )

            baseline_graph = ProjectTopologyGraph(
                project_id=project_id
            )

            # ─────────────────────────────────────────
            # Create emergent root UI node
            # ─────────────────────────────────────────

            root_ui_id = f"root_ui_{uuid.uuid4().hex[:6]}"

            baseline_graph.add_node(
                node_id=root_ui_id,
                node_type=NodeType.UI_NODE,
                properties={
                    "component_name": "RootView",
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

        root_branch = self.arbor_core.initialize_root(
            baseline_graph
        )

        # ─────────────────────────────────────────────
        # 4. Faculty Mutation Proposals
        # ─────────────────────────────────────────────

        log(
            "ARBOR_RUNTIME",
            "🧙 Calling faculties to propose topological patches..."
        )

        proposals: List[PatchIR] = []

        proposals.extend(
            VictoriaUIFaculty.propose_mutations(
                root_branch,
                user_request,
            )
        )

        proposals.extend(
            DerekAPIFaculty.propose_mutations(
                root_branch,
                user_request,
            )
        )

        proposals.extend(
            LunaSchemaFaculty.propose_mutations(
                root_branch,
                user_request,
            )
        )

        proposals.extend(
            ReggieWorkflowFaculty.propose_mutations(
                root_branch,
                user_request,
            )
        )

        # ─────────────────────────────────────────────
        # 5. Marcus Governance Advisory
        # ─────────────────────────────────────────────

        modifiers = {}

        for patch in proposals:

            temp_branch = self.arbor_core.tree_manager.spawn_branch(
                root_branch,
                patch,
            )

            analysis = MarcusGovernanceAnalyst.analyze_governance(
                temp_branch
            )

            modifiers[temp_branch.branch_id] = analysis[
                "marcus_advisory_modifier"
            ]

            self.arbor_core.tree_manager.prune_branch(
                temp_branch.branch_id,
                "Temporary Marcus Evaluation Cleanup",
            )

        # ─────────────────────────────────────────────
        # 6. Explore Candidate Branches
        # ─────────────────────────────────────────────

        log(
            "ARBOR_RUNTIME",
            "🔀 Exploring candidate branches..."
        )

        active_branches = self.arbor_core.explore_possibilities(
            intent,
            proposals,
            modifiers,
        )

        if not active_branches:

            log(
                "ARBOR_RUNTIME",
                "❌ All proposed branches were blocked by "
                "ConstraintEngine or Failure Repulsion."
            )

            return False

        best_branch = active_branches[0]

        log(
            "ARBOR_RUNTIME",
            f"👑 Selected best candidate branch: "
            f"{best_branch.branch_id} "
            f"(weight={best_branch.attention_weight:.2f}, "
            f"entropy={best_branch.entropy_history[-1]:.4f})"
        )

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

        from app.topology.ast_generator import ASTGenerator

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
            "ARBOR_RUNTIME",
            "⚡ Executing synchronous Projection Cycle..."
        )

        kernel = get_kernel()

        success = await kernel.run_projection_cycle(ctx)

        # ─────────────────────────────────────────────
        # 10. Success Path
        # ─────────────────────────────────────────────

        if success:

            log(
                "ARBOR_RUNTIME",
                "✅ Candidate branch successfully "
                "project-committed and verified!"
            )

            best_branch.is_committed = True

            return True

        # ─────────────────────────────────────────────
        # 11. Failure Path
        # ─────────────────────────────────────────────

        log(
            "ARBOR_RUNTIME",
            "❌ Projection cycle failed / "
            "Oracles blocked transaction. "
            "Registering failure in SQLite."
        )

        failed_record = await TopologyVersionRecord.find_one(
            {
                "project_id": project_id,
                "branch_name": "main",
            },
            sort=[("-created_at", 1)],
        )

        if failed_record:

            await failed_record.delete()

            log(
                "ARBOR_RUNTIME",
                "🗑️ Reverted failed candidate topology "
                "record from database."
            )

        # Encode failure vector
        node_count = len(best_branch.topology_graph.nodes)
        edge_count = len(best_branch.topology_graph.edges)

        api_count = sum(
            1
            for n in best_branch.topology_graph.nodes.values()
            if n.node_type == NodeType.API_NODE
        )

        ui_count = sum(
            1
            for n in best_branch.topology_graph.nodes.values()
            if n.node_type == NodeType.UI_NODE
        )

        schema_count = sum(
            1
            for n in best_branch.topology_graph.nodes.values()
            if n.node_type == NodeType.SCHEMA_NODE
        )

        fail_vec = FailureGeometry.encode_failure(
            node_count=node_count,
            edge_count=edge_count,
            is_cyclic=False,
            error_class="runtime",
            mutation_tier=max_tier.value,
            error_len=100,
            api_node_count=api_count,
            ui_node_count=ui_count,
            schema_node_count=schema_count,
        )

        self.failure_db.insert_failure(
            failure_id=str(uuid.uuid4()),
            vector=fail_vec,
            error_class="runtime",
            cycle_id=ctx.cycle_id,
            details=(
                f"Blocked transaction projection for branch: "
                f"{best_branch.branch_id}"
            ),
        )

        # ─────────────────────────────────────────────
        # 12. Escape Mutation Path
        # ─────────────────────────────────────────────

        log(
            "ARBOR_RUNTIME",
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

        escape_active = self.arbor_core.explore_possibilities(
            intent,
            escape_patches,
            modifiers,
        )

        if escape_active:

            escape_branch = escape_active[0]

            log(
                "ARBOR_RUNTIME",
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