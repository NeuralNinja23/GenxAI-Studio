# app/topology/project_graph.py
"""
V4 Canonical Reality Engine — Stage 2: Canonical Topology Engine

Implements the ProjectTopologyGraph (DAG), the sole canonical system state
governing all software structural manifests. Filesystem is a mere projection.
"""

from typing import Dict, List, Set, Any, Optional
import hashlib
import json
from pydantic import BaseModel, Field
from app.sentinel.topology.node_types import NodeType, NodeOntology

class TopologyNode(BaseModel):
    """A single logical entity in the canonical topology."""
    node_id: str
    node_type: NodeType
    properties: Dict[str, Any] = Field(default_factory=dict)
    integrity_hash: str = ""

    def calculate_hash(self) -> str:
        """Compute a cryptographic hash of this node to detect corruption."""
        # Sort keys to ensure deterministic hashing
        serialized_props = json.dumps(self.properties, sort_keys=True)
        raw_data = f"{self.node_id}:{self.node_type.value}:{serialized_props}"
        return hashlib.sha256(raw_data.encode("utf-8")).hexdigest()

    def update_integrity(self) -> None:
        self.integrity_hash = self.calculate_hash()


class TopologyEdge(BaseModel):
    """A directed edge between two topology nodes."""
    source_id: str
    target_id: str
    relation: str  # e.g. "imports", "depends_on", "calls_api", "renders_component", "binds_schema"
    properties: Dict[str, Any] = Field(default_factory=dict)


class ProjectTopologyGraph(BaseModel):
    """
    The Canonical Reality Engine.
    All runtime architectures, filesystem layouts, and code structures orbit this graph.
    """
    project_id: str
    version: int = 1
    nodes: Dict[str, TopologyNode] = Field(default_factory=dict)
    edges: List[TopologyEdge] = Field(default_factory=list)
    graph_hash: str = ""

    def add_node(self, node_id: str, node_type: NodeType, properties: Optional[Dict[str, Any]] = None) -> TopologyNode:
        """Add a node to the topology after validating against the ontology."""
        # Enforce ontology presence
        if node_type not in NodeType.__members__.values():
            raise ValueError(f"Invalid Node Type: {node_type}")

        node = TopologyNode(
            node_id=node_id,
            node_type=node_type,
            properties=properties or {}
        )
        node.update_integrity()
        self.nodes[node_id] = node
        self.update_graph_hash()
        return node

    def get_node(self, node_id: str) -> Optional[TopologyNode]:
        return self.nodes.get(node_id)

    def remove_node(self, node_id: str) -> None:
        """Remove a node and all of its associated edges."""
        if node_id in self.nodes:
            del self.nodes[node_id]
            # Remove incident edges
            self.edges = [e for e in self.edges if e.source_id != node_id and e.target_id != node_id]
            self.update_graph_hash()

    def add_edge(self, source_id: str, target_id: str, relation: str, properties: Optional[Dict[str, Any]] = None) -> TopologyEdge:
        """Add an edge between two existing nodes in the topology."""
        if source_id not in self.nodes:
            self.add_node(source_id, NodeType.AST_NODE, {"generated_on_edge_creation": True})
        if target_id not in self.nodes:
            self.add_node(target_id, NodeType.AST_NODE, {"generated_on_edge_creation": True})

        # Check for duplicate edge
        for edge in self.edges:
            if edge.source_id == source_id and edge.target_id == target_id and edge.relation == relation:
                return edge

        edge = TopologyEdge(
            source_id=source_id,
            target_id=target_id,
            relation=relation,
            properties=properties or {}
        )
        self.edges.append(edge)
        self.update_graph_hash()
        return edge

    def remove_edge(self, source_id: str, target_id: str, relation: str) -> None:
        self.edges = [
            e for e in self.edges
            if not (e.source_id == source_id and e.target_id == target_id and e.relation == relation)
        ]
        self.update_graph_hash()

    def get_outgoing_edges(self, source_id: str) -> List[TopologyEdge]:
        return [e for e in self.edges if e.source_id == source_id]

    def get_incoming_edges(self, target_id: str) -> List[TopologyEdge]:
        return [e for e in self.edges if e.target_id == target_id]

    def get_dependencies_dag(self, relation: Optional[str] = None) -> Dict[str, Set[str]]:
        """Get adjacency list representation of the graph for DAG/cycle checks."""
        adj: Dict[str, Set[str]] = {node_id: set() for node_id in self.nodes}
        for edge in self.edges:
            if relation is None or edge.relation == relation:
                if edge.source_id in adj:
                    adj[edge.source_id].add(edge.target_id)
        return adj

    def compute_hash(self) -> str:
        """Compute graph-level cryptographic integrity hash from all nodes and edges."""
        # Nodes hashed in deterministic order
        sorted_node_hashes = sorted([node.calculate_hash() for node in self.nodes.values()])
        # Edges serialized deterministically
        sorted_edges = sorted(
            [f"{e.source_id}->{e.target_id}:{e.relation}:{json.dumps(e.properties, sort_keys=True)}" for e in self.edges]
        )
        raw_data = {
            "project_id": self.project_id,
            "version": self.version,
            "nodes": sorted_node_hashes,
            "edges": sorted_edges
        }
        serialized = json.dumps(raw_data, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def update_graph_hash(self) -> None:
        self.graph_hash = self.compute_hash()

    def serialize(self) -> Dict[str, Any]:
        """Convert the graph to a serialized dict format for persistence."""
        self.update_graph_hash()
        return self.dict()

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> "ProjectTopologyGraph":
        """Reconstruct a graph from serialized dict format."""
        graph = cls(**data)
        # Recalculate and verify integrity hashes
        for node in graph.nodes.values():
            node.update_integrity()
        graph.update_graph_hash()
        return graph
