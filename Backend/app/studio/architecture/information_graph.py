# app/studio/architecture/information_graph.py
"""
V4 GenxAI Studio — Phase GS-2: InformationGraph

Represents the explicit data, content block structures, and data-to-ontology field bindings.
Decoupled entirely from Sentinel's core node_types.py.
"""

from typing import Dict, Any, Optional
from app.sentinel.topology.project_graph import ProjectTopologyGraph, TopologyNode
from app.sentinel.topology.node_types import NodeType

# Local Studio specific node types
STUDIO_CONTENT_BLOCK_NODE = "CONTENT_BLOCK_NODE"
STUDIO_DATA_FIELD_NODE = "DATA_FIELD_NODE"

class StudioNodeType(str):
    """
    Extends str to have a .value property, satisfying the core
    TopologyNode.calculate_hash() call without polluting sentinel's node_types.py.
    """
    @property
    def value(self) -> str:
        return self

class InformationGraph(ProjectTopologyGraph):
    """
    In-memory representation of application content blocks and fields.
    This graph is framework-agnostic and remains abstract.
    """
    
    def __init__(self, **data: Any):
        super().__init__(**data)

    def add_node(self, node_id: str, node_type: Any, properties: Optional[Dict[str, Any]] = None) -> TopologyNode:
        """
        Override to allow local Studio node types alongside standard NodeType enums.
        Avoids polluting Sentinel's node_types.py.
        """
        is_studio_node = str(node_type) in (STUDIO_CONTENT_BLOCK_NODE, STUDIO_DATA_FIELD_NODE)
        is_sentinel_node = False
        try:
            is_sentinel_node = node_type in NodeType.__members__.values()
        except Exception:
            pass

        if not (is_studio_node or is_sentinel_node):
            raise ValueError(f"Invalid Node Type: {node_type}")

        # Construct TopologyNode using construct() to bypass strict Pydantic Enum validation if it's a Studio node type
        if is_studio_node:
            node_type = StudioNodeType(node_type)
            node = TopologyNode.construct(
                node_id=node_id,
                node_type=node_type,
                properties=properties or {}
            )
        else:
            node = TopologyNode(
                node_id=node_id,
                node_type=node_type,
                properties=properties or {}
            )
        node.update_integrity()
        self.nodes[node_id] = node
        self.update_graph_hash()
        return node

    def add_information_node(self, node_id: str, node_type: str, properties: Optional[Dict[str, Any]] = None) -> None:
        """Helper to add only information domain nodes."""
        if node_type not in (STUDIO_CONTENT_BLOCK_NODE, STUDIO_DATA_FIELD_NODE):
            raise ValueError(f"Cannot add non-information node {node_type} to InformationGraph.")
        
        self.add_node(node_id, node_type, properties)
