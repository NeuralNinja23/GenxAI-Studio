# app/studio/architecture/ux_blueprint.py
"""
V4 GenxAI Studio — Phase GS-6: UXBlueprint

Represents the framework-agnostic cognitive interaction blueprint.
Models UX intentions, end-to-end journeys, task flows, attention focus shifts,
decision branching gates, and explicit transaction outcomes.
"""

from typing import Dict, Any, Optional
from app.sentinel.topology.project_graph import ProjectTopologyGraph, TopologyNode
from app.sentinel.topology.node_types import NodeType
from app.studio.architecture.information_graph import StudioNodeType

# Local Studio UX Node Types
STUDIO_UX_SYSTEM_NODE = "UX_SYSTEM_NODE"
STUDIO_UX_INTENT_NODE = "UX_INTENT_NODE"
STUDIO_USER_JOURNEY_NODE = "USER_JOURNEY_NODE"
STUDIO_TASK_FLOW_NODE = "TASK_FLOW_NODE"
STUDIO_ATTENTION_FLOW_NODE = "ATTENTION_FLOW_NODE"
STUDIO_DECISION_POINT_NODE = "DECISION_POINT_NODE"
STUDIO_OUTCOME_NODE = "OUTCOME_NODE"

class UXBlueprint(ProjectTopologyGraph):
    """
    In-memory representation of user experience flows, attention shifting,
    and terminal interaction outcomes.
    This graph is framework-agnostic and remains abstract.
    """
    
    def __init__(self, **data: Any):
        super().__init__(**data)

    def add_node(self, node_id: str, node_type: Any, properties: Optional[Dict[str, Any]] = None) -> TopologyNode:
        """
        Override to allow local Studio UX node types alongside application/information/intent types.
        Bypasses core Sentinel enum validation constraints.
        """
        studio_ux_types = (
            STUDIO_UX_SYSTEM_NODE,
            STUDIO_UX_INTENT_NODE,
            STUDIO_USER_JOURNEY_NODE,
            STUDIO_TASK_FLOW_NODE,
            STUDIO_ATTENTION_FLOW_NODE,
            STUDIO_DECISION_POINT_NODE,
            STUDIO_OUTCOME_NODE
        )
        
        is_studio_ux = str(node_type) in studio_ux_types
        is_sentinel_node = False
        try:
            is_sentinel_node = node_type in NodeType.__members__.values()
        except Exception:
            pass

        # Allow parents as references
        is_design_intent_type = str(node_type) in (
            "DESIGN_INTENT_NODE", "GLOBAL_INTENT_NODE", "PAGE_NODE", "CONTENT_BLOCK_NODE"
        )

        if not (is_studio_ux or is_sentinel_node or is_design_intent_type):
            raise ValueError(f"Invalid Node Type in UXBlueprint: {node_type}")

        # Construct TopologyNode using construct() to bypass strict Pydantic Enum validation if it's a Studio node type
        if is_studio_ux or is_design_intent_type:
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

    def add_ux_node(self, node_id: str, node_type: str, properties: Optional[Dict[str, Any]] = None) -> None:
        """Helper to add only UX domain nodes."""
        studio_ux_types = (
            STUDIO_UX_SYSTEM_NODE,
            STUDIO_UX_INTENT_NODE,
            STUDIO_USER_JOURNEY_NODE,
            STUDIO_TASK_FLOW_NODE,
            STUDIO_ATTENTION_FLOW_NODE,
            STUDIO_DECISION_POINT_NODE,
            STUDIO_OUTCOME_NODE
        )
        if node_type not in studio_ux_types:
            raise ValueError(f"Cannot add non-ux node {node_type} to UXBlueprint.")
        
        self.add_node(node_id, node_type, properties)
