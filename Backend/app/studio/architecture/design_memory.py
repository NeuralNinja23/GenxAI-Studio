# app/studio/architecture/design_memory.py
"""
V4 GenxAI Studio — Phase GS-10: DesignMemoryGraph

Represents framework-agnostic design learning memory, compilation records,
cognitive critiques, user feedback, and learned design recommendations.
"""

from typing import Dict, Any, Optional
from app.sentinel.topology.project_graph import ProjectTopologyGraph, TopologyNode
from app.sentinel.topology.node_types import NodeType
from app.studio.architecture.information_graph import StudioNodeType

# Local Studio Design Memory Node Types
STUDIO_DESIGN_MEMORY_NODE = "DESIGN_MEMORY_NODE"
STUDIO_COMPILE_RECORD_NODE = "COMPILE_RECORD_NODE"
STUDIO_COGNITIVE_CRITIQUE_NODE = "COGNITIVE_CRITIQUE_NODE"
STUDIO_USER_FEEDBACK_NODE = "USER_FEEDBACK_NODE"
STUDIO_DESIGN_LEARNING_NODE = "DESIGN_LEARNING_NODE"

class DesignMemoryGraph(ProjectTopologyGraph):
    """
    In-memory representation of design learning, compile metadata, critiques, and feedback.
    Keeps a safe boundary from Sentinel memory and execution schemas.
    """
    
    def __init__(self, **data: Any):
        super().__init__(**data)

    def add_node(self, node_id: str, node_type: Any, properties: Optional[Dict[str, Any]] = None) -> TopologyNode:
        """
        Override to allow local Studio Design Memory node types.
        Bypasses core Sentinel enum validation constraints.
        """
        studio_memory_types = (
            STUDIO_DESIGN_MEMORY_NODE,
            STUDIO_COMPILE_RECORD_NODE,
            STUDIO_COGNITIVE_CRITIQUE_NODE,
            STUDIO_USER_FEEDBACK_NODE,
            STUDIO_DESIGN_LEARNING_NODE
        )
        
        is_studio_memory = str(node_type) in studio_memory_types
        is_sentinel_node = False
        try:
            is_sentinel_node = node_type in NodeType.__members__.values()
        except Exception:
            pass

        # Allow parent design node types as reference targets
        is_parent_type = str(node_type) in (
            "DESIGN_INTENT_NODE", "COMPONENT_NODE", "LAYOUT_CONTAINER_NODE"
        )

        if not (is_studio_memory or is_sentinel_node or is_parent_type):
            raise ValueError(f"Invalid Node Type in DesignMemoryGraph: {node_type}")

        # Construct TopologyNode using construct() to bypass strict Pydantic Enum validation if it's a Studio node type
        if is_studio_memory or is_parent_type:
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

    def add_memory_node(self, node_id: str, node_type: str, properties: Optional[Dict[str, Any]] = None) -> None:
        """Helper to add only Design Memory domain nodes."""
        studio_memory_types = (
            STUDIO_DESIGN_MEMORY_NODE,
            STUDIO_COMPILE_RECORD_NODE,
            STUDIO_COGNITIVE_CRITIQUE_NODE,
            STUDIO_USER_FEEDBACK_NODE,
            STUDIO_DESIGN_LEARNING_NODE
        )
        if node_type not in studio_memory_types:
            raise ValueError(f"Cannot add non-memory node {node_type} to DesignMemoryGraph.")
        
        self.add_node(node_id, node_type, properties)
