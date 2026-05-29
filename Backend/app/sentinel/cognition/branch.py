# app/cognition/branch.py
"""
V4 Bounded Cognition — Stage 6: Minimal Cognition
Defines the BranchState model ("candidate universes") and BranchTreeManager.
Tracks topological lineage ancestry and structural scoring metrics.
"""

import copy
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.sentinel.cognition.patch_ir import PatchIR
from app.sentinel.topology.project_graph import ProjectTopologyGraph
from app.sentinel.topology.node_types import NodeType

class BranchState(BaseModel):
    """
    Represents an isolated, non-authoritative candidate structural universe.
    """
    branch_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parent_branch_id: Optional[str] = None
    topology_graph: ProjectTopologyGraph
    entropy_history: List[float] = Field(default_factory=list)
    repulsion_score: float = 0.0
    attention_weight: float = 1.0
    oracle_history: List[Dict[str, Any]] = Field(default_factory=list)
    governance: Dict[str, Any] = Field(default_factory=dict)
    lineage_path: List[str] = Field(default_factory=list)
    is_frozen: bool = False
    is_pruned: bool = False
    is_committed: bool = False
    needs_stabilization: bool = False

    def clone_graph(self) -> ProjectTopologyGraph:
        """Create a deep copy of the active topology graph."""
        # Using the class methods to properly clone Pydantic models
        serialized = self.topology_graph.serialize()
        return ProjectTopologyGraph.deserialize(serialized)


class BranchTreeManager:
    """
    Tracks and coordinates candidate universes in the search space.
    """

    def __init__(self):
        self.active_branches: Dict[str, BranchState] = {}
        self.pruned_branches: Dict[str, str] = {}  # branch_id -> reason

    def spawn_branch(self, parent_branch: BranchState, patch: Optional[PatchIR] = None) -> BranchState:
        """
        Spawns a new child branch from an existing candidate universe.
        If a PatchIR is supplied, applies the topological mutation to the child's graph.
        """
        cloned_graph = parent_branch.clone_graph()

        if patch:
            action = patch.action.upper()
            target = patch.target_node_id

            if action == "ADD_NODE":
                node_type_str = str(patch.node_data.get("node_type", "AST_NODE")).strip().upper()
                try:
                    node_type = NodeType(node_type_str)
                except ValueError:
                    node_type = NodeType.AST_NODE
                cloned_graph.add_node(
                    node_id=target,
                    node_type=node_type,
                    properties=patch.node_data.get("properties", {})
                )

            elif action in ("REMOVE_NODE", "DELETE_NODE"):
                cloned_graph.remove_node(target)

            elif action in ("UPDATE_NODE", "MODIFY_NODE"):
                node = cloned_graph.get_node(target)
                if node:
                    props = patch.node_data.get("properties", {})
                    node.properties.update(props)
                    node.update_integrity()
                    cloned_graph.update_graph_hash()

            elif action == "ADD_EDGE":
                source = patch.edge_data.get("source")
                target_edge = patch.edge_data.get("target")
                relation = patch.edge_data.get("relation", "imports")
                if source and target_edge:
                    cloned_graph.add_edge(
                        source_id=source,
                        target_id=target_edge,
                        relation=relation,
                        properties=patch.edge_data.get("properties", {})
                    )

            elif action in ("REMOVE_EDGE", "DELETE_EDGE"):
                source = patch.edge_data.get("source")
                target_edge = patch.edge_data.get("target")
                relation = patch.edge_data.get("relation", "imports")
                if source and target_edge:
                    cloned_graph.remove_edge(source, target_edge, relation)

            # Automatically ground renderable UI nodes to state nodes
            from app.sentinel.topology.topology_compiler import TopologyCompiler
            TopologyCompiler._ensure_renderable_grounding(cloned_graph)

        # Create child state
        lineage = parent_branch.lineage_path + [parent_branch.branch_id]
        child = BranchState(
            parent_branch_id=parent_branch.branch_id,
            topology_graph=cloned_graph,
            entropy_history=copy.deepcopy(parent_branch.entropy_history),
            repulsion_score=parent_branch.repulsion_score,
            attention_weight=parent_branch.attention_weight,
            lineage_path=lineage
        )
        self.active_branches[child.branch_id] = child
        return child

    def prune_branch(self, branch_id: str, reason: str) -> None:
        """Prunes a branch from active search."""
        if branch_id in self.active_branches:
            branch = self.active_branches[branch_id]
            branch.is_pruned = True
            self.pruned_branches[branch_id] = reason
            del self.active_branches[branch_id]

    def freeze_branch(self, branch_id: str) -> None:
        """Freezes a branch to indicate stable convergence."""
        if branch_id in self.active_branches:
            self.active_branches[branch_id].is_frozen = True
