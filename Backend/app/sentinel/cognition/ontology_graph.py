# app/sentinel/cognition/ontology_graph.py
"""
V4 Cognition Subsystem — Phase 8: Product Ontology Reasoner

The Ontology Graph is an internal, purely in-memory cognitive structure.
It models abstract semantic meaning — Entities, Relationships, Roles, Capabilities, and Workflows
separately from concrete software implementation details.
"""

from typing import Dict, Any, Optional
from app.sentinel.topology.project_graph import ProjectTopologyGraph
from app.sentinel.topology.node_types import NodeType

class OntologyGraph(ProjectTopologyGraph):
    """
    In-memory semantic model of product ontology.
    This graph is NOT projected to files, ensuring it remains an abstract meaning model.
    
    Valid Node Types:
    - ENTITY_NODE
    - ROLE_NODE
    - RELATIONSHIP_NODE
    - CAPABILITY_NODE
    - ONTOLOGY_WORKFLOW_NODE
    """
    
    def __init__(self, **data: Any):
        super().__init__(**data)

    def add_ontology_node(self, node_id: str, node_type: NodeType, properties: Optional[Dict[str, Any]] = None) -> None:
        """Helper to add only ontology domain nodes."""
        if node_type not in (
            NodeType.ENTITY_NODE,
            NodeType.ROLE_NODE,
            NodeType.RELATIONSHIP_NODE,
            NodeType.CAPABILITY_NODE,
            NodeType.ONTOLOGY_WORKFLOW_NODE
        ):
            raise ValueError(f"Cannot add non-ontology node {node_type} to OntologyGraph.")
        
        self.add_node(node_id, node_type, properties)
