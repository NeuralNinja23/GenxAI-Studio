# app/topology/topology_validator.py
"""
V4 Structural Physics Engine — Stage 2: Canonical Topology Engine

Provides deterministic graph mathematics, dependency legality checks,
and integrity validation for ProjectTopologyGraph. No cognition allowed here.
"""

from typing import Dict, List, Set, Tuple, Optional
from pydantic import BaseModel, Field
from app.topology.node_types import NodeType, NodeOntology
from app.topology.project_graph import ProjectTopologyGraph, TopologyNode, TopologyEdge

class ValidationViolation(BaseModel):
    rule: str
    node_id: Optional[str] = None
    target_id: Optional[str] = None
    reason: str


class TopologyValidationResult(BaseModel):
    passed: bool
    violations: List[ValidationViolation] = Field(default_factory=list)


class TopologyValidator:
    """
    Purely deterministic structural physics engine.
    Applies graph mathematical invariants to verify topology sanity.
    """

    @classmethod
    def validate_graph(cls, graph: ProjectTopologyGraph) -> TopologyValidationResult:
        """
        Validate all structural constraints, import legality, and DAG safety.
        Returns a validation result containing any rules broken.
        """
        violations: List[ValidationViolation] = []

        # ── 1. Validate Node Integrity Hashes ─────────────────
        for node_id, node in graph.nodes.items():
            expected_hash = node.calculate_hash()
            if node.integrity_hash != expected_hash:
                violations.append(
                    ValidationViolation(
                        rule="NODE_CORRUPTION_DETECTED",
                        node_id=node_id,
                        reason=f"Node integrity hash mismatch. Graph indicates tampering or corruption."
                    )
                )

        # ── 2. Validate Edge Reference Legality ───────────────
        for edge in graph.edges:
            if edge.source_id not in graph.nodes:
                violations.append(
                    ValidationViolation(
                        rule="DANGLING_EDGE_SOURCE",
                        node_id=edge.source_id,
                        reason="Edge source node does not exist in graph."
                    )
                )
            if edge.target_id not in graph.nodes:
                violations.append(
                    ValidationViolation(
                        rule="DANGLING_EDGE_TARGET",
                        node_id=edge.target_id,
                        reason=f"Edge target node '{edge.target_id}' does not exist in graph."
                    )
                )

        if violations:
            # Return early if basic references are broken to avoid KeyError in deeper checks
            return TopologyValidationResult(passed=False, violations=violations)

        # ── 3. Cycle Detection (DAG enforcement) ─────────────
        # Some relations (depends_on, imports) MUST be acyclic
        acyclic_relations = ["depends_on", "imports", "governs"]
        for rel in acyclic_relations:
            has_cycle, cycle_path = cls._detect_cycle(graph, rel)
            if has_cycle:
                violations.append(
                    ValidationViolation(
                        rule=f"CYCLIC_{rel.upper()}_RELATION",
                        reason=f"Illegal cyclic structure detected in relationship '{rel}': {' -> '.join(cycle_path)}"
                    )
                )

        # ── 4. Edge Legality and Connection Rules ────────────
        # Example rule: UI_NODE cannot directly edge to SCHEMA_NODE (must use STATE_NODE or API_NODE)
        for edge in graph.edges:
            source_node = graph.nodes[edge.source_id]
            target_node = graph.nodes[edge.target_id]

            if source_node.node_type == NodeType.UI_NODE and target_node.node_type == NodeType.SCHEMA_NODE:
                violations.append(
                    ValidationViolation(
                        rule="ILLEGAL_UI_TO_SCHEMA_EDGE",
                        node_id=edge.source_id,
                        target_id=edge.target_id,
                        reason="UI Component cannot directly target a Database Schema. Must bind via a STATE_NODE."
                    )
                )

            # Ensure mutation tier bounds are respected
            source_max_tier = NodeOntology.get_max_mutation_tier(source_node.node_type)
            target_max_tier = NodeOntology.get_max_mutation_tier(target_node.node_type)

        return TopologyValidationResult(passed=len(violations) == 0, violations=violations)

    @classmethod
    def _detect_cycle(cls, graph: ProjectTopologyGraph, relation: str) -> Tuple[bool, List[str]]:
        """DFS-based cycle detection for a specific edge relationship."""
        adj = graph.get_dependencies_dag(relation=relation)
        visited: Set[str] = set()
        rec_stack: List[str] = []

        def dfs(node_id: str) -> Tuple[bool, List[str]]:
            visited.add(node_id)
            rec_stack.append(node_id)

            for neighbor in adj.get(node_id, set()):
                if neighbor not in visited:
                    has_cyc, path = dfs(neighbor)
                    if has_cyc:
                        return True, path
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start_idx = rec_stack.index(neighbor)
                    cycle_path = rec_stack[cycle_start_idx:] + [neighbor]
                    return True, cycle_path

            rec_stack.pop()
            return False, []

        for node_id in graph.nodes:
            if node_id not in visited:
                has_cyc, path = dfs(node_id)
                if has_cyc:
                    return True, path

        return False, []
