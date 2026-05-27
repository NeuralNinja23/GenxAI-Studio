# app/cognition/arbor_core.py
"""
V4 Bounded Cognition — Stage 6: Minimal Cognition
Implements ArborCore, the cognitive navigation layer.
Coordinates branch tree search, constraint checks, repulsion vector evaluation, and attention routing.
"""

from typing import Dict, List, Tuple, Optional, Any
import numpy as np
from app.cognition.branch import BranchState, BranchTreeManager
from app.cognition.patch_ir import PatchIR
from app.cognition.constraint_engine import ConstraintEngine
from app.cognition.convergence_engine import ConvergenceEngine
from app.cognition.attention_router import AttentionRouter
from app.failure_memory.failure_geometry import FailureGeometry
from app.failure_memory.repulsion_engine import RepulsionEngine
from app.topology.project_graph import ProjectTopologyGraph
from app.topology.node_types import NodeType
from app.models.directive import IntentField

class ArborCore:
    """
    Cognitive Navigation Layer.
    Orchestrates candidate graph traversal without direct write/reality authority.
    """

    def __init__(self, max_branches: int = 5):
        self.tree_manager = BranchTreeManager()
        self.failure_db = FailureGeometry()
        self.repulsion_engine = RepulsionEngine(self.failure_db)
        self.attention_router = AttentionRouter(max_branches)

    def initialize_root(self, root_graph: ProjectTopologyGraph) -> BranchState:
        """Initialize the root branch of the search tree."""
        # Clean existing tree
        self.tree_manager = BranchTreeManager()
        root = BranchState(
            branch_id="root",
            topology_graph=root_graph
        )
        entropy = ConvergenceEngine.calculate_entropy(root_graph)
        root.entropy_history.append(entropy)
        self.tree_manager.active_branches[root.branch_id] = root
        return root

    def explore_possibilities(
        self,
        intent: IntentField,
        proposals: List[PatchIR],
        marcus_advisory_modifiers: Optional[Dict[str, float]] = None
    ) -> List[BranchState]:
        """
        Takes candidate topological mutation proposals (PatchIR) and explores them in parallel branch states.
        Applies constraint filters, computes failure repulsion vectors, updates entropy, and routes attention.
        """
        active_list = list(self.tree_manager.active_branches.values())
        if not active_list:
            raise ValueError("No active branches in the tree. Initialize the root first.")

        # Source parent branch is the currently highest ranked active branch
        # Sort current active list by weight
        self.attention_router.route_attention(active_list, marcus_advisory_modifiers)
        parent = active_list[0]

        new_children = []
        for patch in proposals:
            # 1. Enforce laws of physics (ConstraintEngine)
            validation = ConstraintEngine.validate_mutation(patch, intent)
            if not validation.passed:
                # Discard proposed branch path
                continue

            # 2. Spawn candidate universe
            child = self.tree_manager.spawn_branch(parent, patch)

            # 3. Calculate new topological entropy
            child_entropy = ConvergenceEngine.calculate_entropy(child.topology_graph)
            child.entropy_history.append(child_entropy)

            # 4. Encode state features to calculate failure memory repulsion vector
            # Read structural metrics of graph to encode vector
            node_count = len(child.topology_graph.nodes)
            edge_count = len(child.topology_graph.edges)
            # Basic cycle check
            has_cycles = False
            try:
                adj = child.topology_graph.get_dependencies_dag()
                visited = set()
                rec_stack = set()
                def is_cyclic(v):
                    visited.add(v)
                    rec_stack.add(v)
                    for neighbour in adj.get(v, []):
                        if neighbour not in visited:
                            if is_cyclic(neighbour):
                                return True
                        elif neighbour in rec_stack:
                            return True
                    rec_stack.remove(v)
                    return False
                for node in child.topology_graph.nodes:
                    if node not in visited:
                        if is_cyclic(node):
                            has_cycles = True
                            break
            except Exception:
                has_cycles = True

            api_count = sum(1 for n in child.topology_graph.nodes.values() if n.node_type.value == "API_NODE")
            ui_count = sum(1 for n in child.topology_graph.nodes.values() if n.node_type.value == "UI_NODE")
            schema_count = sum(1 for n in child.topology_graph.nodes.values() if n.node_type.value == "SCHEMA_NODE")

            candidate_vec = FailureGeometry.encode_failure(
                node_count=node_count,
                edge_count=edge_count,
                is_cyclic=has_cycles,
                error_class="syntax",  # Propose safe baseline for exploration
                mutation_tier=patch.mutation_tier.value,
                error_len=0,
                api_node_count=api_count,
                ui_node_count=ui_count,
                schema_node_count=schema_count
            )

            # Calculate failure repulsion score
            child.repulsion_score = self.repulsion_engine.get_repulsion_score(candidate_vec)

            # Check if this vector triggers severe repulsion breach
            if self.repulsion_engine.check_repulsion_breach(candidate_vec, threshold=0.85) or has_cycles:
                # Terminate branch instantly
                self.tree_manager.prune_branch(child.branch_id, "Failure Repulsion Breach or Topology Cycle.")
                continue

            new_children.append(child)

        # 5. Route attention and prune excess branches based on budget
        all_active = list(self.tree_manager.active_branches.values())
        kept, pruned = self.attention_router.prune_to_budget(all_active, marcus_advisory_modifiers)

        for p in pruned:
            self.tree_manager.prune_branch(p.branch_id, "Budget capacity limit exceeded.")

        return kept
