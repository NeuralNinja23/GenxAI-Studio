# app/studio/architecture/component_graph.py
"""
V4 GenxAI Studio — Phase GS-7: ComponentGraph

Represents framework-agnostic component and layout structures.
Models abstract spatial layout models, surface interfaces, visual state variations,
and abstract user interaction properties completely decoupled from rendering frameworks.
"""

from typing import Dict, Any, Optional
from app.sentinel.topology.project_graph import ProjectTopologyGraph, TopologyNode
from app.sentinel.topology.node_types import NodeType
from app.studio.architecture.information_graph import StudioNodeType

# Local Studio Component Node Types
STUDIO_COMPONENT_SYSTEM_NODE = "COMPONENT_SYSTEM_NODE"
STUDIO_LAYOUT_CONTAINER_NODE = "LAYOUT_CONTAINER_NODE"
STUDIO_COMPONENT_NODE = "COMPONENT_NODE"
STUDIO_STATE_NODE = "STATE_NODE"
STUDIO_UI_PROPERTY_NODE = "UI_PROPERTY_NODE"

class ComponentGraph(ProjectTopologyGraph):
    """
    In-memory representation of spatial layout structures, abstract component surfaces,
    visual UI states, and logical properties.
    This graph is framework-agnostic and remains abstract.
    """
    
    def __init__(self, **data: Any):
        super().__init__(**data)

    def add_node(self, node_id: str, node_type: Any, properties: Optional[Dict[str, Any]] = None) -> TopologyNode:
        """
        Override to allow local Studio Component node types alongside application/information/intent types.
        Bypasses core Sentinel enum validation constraints.
        """
        studio_comp_types = (
            STUDIO_COMPONENT_SYSTEM_NODE,
            STUDIO_LAYOUT_CONTAINER_NODE,
            STUDIO_COMPONENT_NODE,
            STUDIO_STATE_NODE,
            STUDIO_UI_PROPERTY_NODE
        )
        
        is_studio_comp = str(node_type) in studio_comp_types
        is_sentinel_node = False
        try:
            is_sentinel_node = node_type in NodeType.__members__.values()
        except Exception:
            pass

        # Allow parents as references
        is_design_intent_type = str(node_type) in (
            "DESIGN_INTENT_NODE", "GLOBAL_INTENT_NODE", "PAGE_NODE", "CONTENT_BLOCK_NODE",
            "DESIGN_SYSTEM_NODE", "SPACING_TOKEN_NODE", "TASK_FLOW_NODE"
        )

        if not (is_studio_comp or is_sentinel_node or is_design_intent_type):
            raise ValueError(f"Invalid Node Type in ComponentGraph: {node_type}")

        # Construct TopologyNode using construct() to bypass strict Pydantic Enum validation if it's a Studio node type
        if is_studio_comp or is_design_intent_type:
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

    def add_component_node(self, node_id: str, node_type: str, properties: Optional[Dict[str, Any]] = None) -> None:
        """Helper to add only Component domain nodes."""
        studio_comp_types = (
            STUDIO_COMPONENT_SYSTEM_NODE,
            STUDIO_LAYOUT_CONTAINER_NODE,
            STUDIO_COMPONENT_NODE,
            STUDIO_STATE_NODE,
            STUDIO_UI_PROPERTY_NODE
        )
        if node_type not in studio_comp_types:
            raise ValueError(f"Cannot add non-component node {node_type} to ComponentGraph.")
        
        self.add_node(node_id, node_type, properties)
