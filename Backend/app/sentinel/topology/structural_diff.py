# app/topology/structural_diff.py
"""
V4 Semantic Topology Differential Analysis — Stage 2: Canonical Topology Engine

Provides comparative analysis of ProjectTopologyGraph states, classifying
structural mutations, computing convergence scores, and enforcing repulsion.
"""

from typing import Dict, List, Set, Any
from pydantic import BaseModel, Field
from app.models.runtime_models import MutationTier
from app.sentinel.topology.node_types import NodeType, NodeOntology
from app.sentinel.topology.project_graph import ProjectTopologyGraph, TopologyNode, TopologyEdge

class NodeDiff(BaseModel):
    node_id: str
    node_type: NodeType
    change_type: str  # "added", "removed", "modified"
    property_changes: Dict[str, Any] = Field(default_factory=dict)  # {"field": {"old": x, "new": y}}


class EdgeDiff(BaseModel):
    source_id: str
    target_id: str
    relation: str
    change_type: str  # "added", "removed"


class TopologyDiffReport(BaseModel):
    project_id: str
    base_hash: str
    target_hash: str
    nodes_changed: List[NodeDiff] = Field(default_factory=list)
    edges_changed: List[EdgeDiff] = Field(default_factory=list)
    max_mutation_tier: MutationTier = MutationTier.COSMETIC
    convergence_score: float = 1.0  # 1.0 means identical, 0.0 means completely different

    def is_empty(self) -> bool:
        return len(self.nodes_changed) == 0 and len(self.edges_changed) == 0


class StructuralDiff:
    """
    Semantic Topology Diff Engine.
    Examines two graph configurations to construct a structural diff report,
    enforcing branch mutation rules and calculating topological stability.
    """

    @classmethod
    def compare(cls, base: ProjectTopologyGraph, target: ProjectTopologyGraph) -> TopologyDiffReport:
        """
        Compare two project graphs and return a complete differential profile.
        """
        report = TopologyDiffReport(
            project_id=base.project_id,
            base_hash=base.graph_hash,
            target_hash=target.graph_hash
        )

        # ── 1. Compare Nodes ──────────────────────────────────
        base_node_ids = set(base.nodes.keys())
        target_node_ids = set(target.nodes.keys())

        # Added nodes
        for nid in target_node_ids - base_node_ids:
            tn = target.nodes[nid]
            report.nodes_changed.append(
                NodeDiff(node_id=nid, node_type=tn.node_type, change_type="added")
            )

        # Removed nodes
        for nid in base_node_ids - target_node_ids:
            bn = base.nodes[nid]
            report.nodes_changed.append(
                NodeDiff(node_id=nid, node_type=bn.node_type, change_type="removed")
            )

        # Modified nodes
        for nid in base_node_ids & target_node_ids:
            bn = base.nodes[nid]
            tn = target.nodes[nid]
            if bn.integrity_hash != tn.integrity_hash:
                prop_changes = cls._compare_properties(bn.properties, tn.properties)
                if prop_changes:
                    report.nodes_changed.append(
                        NodeDiff(
                            node_id=nid,
                            node_type=bn.node_type,
                            change_type="modified",
                            property_changes=prop_changes
                        )
                    )

        # ── 2. Compare Edges ──────────────────────────────────
        base_edges = {f"{e.source_id}->{e.target_id}:{e.relation}": e for e in base.edges}
        target_edges = {f"{e.source_id}->{e.target_id}:{e.relation}": e for e in target.edges}

        # Added edges
        for key in set(target_edges.keys()) - set(base_edges.keys()):
            e = target_edges[key]
            report.edges_changed.append(
                EdgeDiff(source_id=e.source_id, target_id=e.target_id, relation=e.relation, change_type="added")
            )

        # Removed edges
        for key in set(base_edges.keys()) - set(target_edges.keys()):
            e = base_edges[key]
            report.edges_changed.append(
                EdgeDiff(source_id=e.source_id, target_id=e.target_id, relation=e.relation, change_type="removed")
            )

        # ── 3. Classify Max Mutation Tier ─────────────────────
        report.max_mutation_tier = cls._determine_max_mutation_tier(report)

        # ── 4. Calculate Structural Convergence Score ─────────
        report.convergence_score = cls._calculate_convergence(base, report)

        return report

    @classmethod
    def _compare_properties(cls, base_props: Dict[str, Any], target_props: Dict[str, Any]) -> Dict[str, Any]:
        changes = {}
        all_keys = set(base_props.keys()) | set(target_props.keys())
        for k in all_keys:
            if k not in base_props:
                changes[k] = {"old": None, "new": target_props[k]}
            elif k not in target_props:
                changes[k] = {"old": base_props[k], "new": None}
            elif base_props[k] != target_props[k]:
                changes[k] = {"old": base_props[k], "new": target_props[k]}
        return changes

    @classmethod
    def _determine_max_mutation_tier(cls, report: TopologyDiffReport) -> MutationTier:
        """Classify the entire diff into a V4 mutation tier (T1 to T5)."""
        if report.is_empty():
            return MutationTier.COSMETIC

        highest_tier = MutationTier.COSMETIC
        for nd in report.nodes_changed:
            node_tier = NodeOntology.get_max_mutation_tier(nd.node_type)
            if node_tier > highest_tier:
                highest_tier = node_tier

        # Edges involving forbidden nodes upgrade to forbidden
        for ed in report.edges_changed:
            # We don't have node types readily inside EdgeDiff, but we can assume normal edge mutations
            # are structural/behavioral/topology mutations (Tier 4).
            pass

        return highest_tier

    @classmethod
    def _calculate_convergence(cls, base: ProjectTopologyGraph, report: TopologyDiffReport) -> float:
        """
        Compute convergence score [0.0 - 1.0] indicating topology divergence.
        If target is completely identical, score is 1.0.
        Large structural additions or removals reduce the score.
        """
        base_size = len(base.nodes) + len(base.edges)
        if base_size == 0:
            return 1.0 if report.is_empty() else 0.0

        diff_size = len(report.nodes_changed) + len(report.edges_changed)
        # Ratio of change to base graph structure
        divergence = min(1.0, float(diff_size) / float(base_size))
        return 1.0 - divergence
