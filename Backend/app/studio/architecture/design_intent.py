# app/studio/architecture/design_intent.py
"""
V4 GenxAI Studio — Phase GS-3: DesignIntentGraph

Represents framework-agnostic design, UX, hierarchy, and attention intent annotations.
Provides causal traceability back to a central DESIGN_INTENT_NODE root.
Decoupled entirely from Sentinel's core node_types.py.
"""

from typing import Dict, Any, Optional
from app.sentinel.topology.project_graph import ProjectTopologyGraph, TopologyNode
from app.sentinel.topology.node_types import NodeType
from app.studio.architecture.information_graph import (
    StudioNodeType,
    STUDIO_CONTENT_BLOCK_NODE,
    STUDIO_DATA_FIELD_NODE
)

# Local Studio Design Intent Node Types
STUDIO_DESIGN_INTENT_NODE = "DESIGN_INTENT_NODE"
STUDIO_GLOBAL_INTENT_NODE = "GLOBAL_INTENT_NODE"
STUDIO_PAGE_INTERACTION_NODE = "PAGE_INTERACTION_NODE"
STUDIO_ATTENTION_MAP_NODE = "ATTENTION_MAP_NODE"

class DesignIntentGraph(ProjectTopologyGraph):
    """
    In-memory representation of design intentions, interaction models, and attention rankings.
    This graph is framework-agnostic and remains abstract.
    """
    
    def __init__(self, **data: Any):
        super().__init__(**data)

    def add_node(self, node_id: str, node_type: Any, properties: Optional[Dict[str, Any]] = None) -> TopologyNode:
        """
        Override to allow local Studio design node types alongside information and sentinel node types.
        Bypasses core Sentinel enum validation constraints.
        """
        studio_design_types = (
            STUDIO_DESIGN_INTENT_NODE,
            STUDIO_GLOBAL_INTENT_NODE,
            STUDIO_PAGE_INTERACTION_NODE,
            STUDIO_ATTENTION_MAP_NODE
        )
        studio_info_types = (
            STUDIO_CONTENT_BLOCK_NODE,
            STUDIO_DATA_FIELD_NODE
        )
        
        is_studio_design = str(node_type) in studio_design_types
        is_studio_info = str(node_type) in studio_info_types
        is_sentinel_node = False
        try:
            is_sentinel_node = node_type in NodeType.__members__.values()
        except Exception:
            pass

        if not (is_studio_design or is_studio_info or is_sentinel_node):
            raise ValueError(f"Invalid Node Type in DesignIntentGraph: {node_type}")

        # Construct TopologyNode using construct() to bypass strict Pydantic Enum validation if it's a Studio node type
        if is_studio_design or is_studio_info:
            node_type_val = StudioNodeType(node_type)
            node = TopologyNode.construct(
                node_id=node_id,
                node_type=node_type_val,
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

    def add_design_node(self, node_id: str, node_type: str, properties: Optional[Dict[str, Any]] = None) -> None:
        """Helper to add only design domain nodes."""
        studio_design_types = (
            STUDIO_DESIGN_INTENT_NODE,
            STUDIO_GLOBAL_INTENT_NODE,
            STUDIO_PAGE_INTERACTION_NODE,
            STUDIO_ATTENTION_MAP_NODE
        )
        if node_type not in studio_design_types:
            raise ValueError(f"Cannot add non-design node {node_type} to DesignIntentGraph.")
        
        self.add_node(node_id, node_type, properties)
