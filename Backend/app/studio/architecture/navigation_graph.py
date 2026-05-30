# app/studio/architecture/navigation_graph.py
"""
V4 GenxAI Studio — Phase GS-5: NavigationGraph

Represents logical, framework-agnostic routing structures and menu link hierarchies.
Completely isolated from visual navigation systems (like React Router),
defining routing models, standard and workflow route pathways, and user landing entry points.
"""

from typing import Dict, Any, Optional
from app.sentinel.topology.project_graph import ProjectTopologyGraph, TopologyNode
from app.sentinel.topology.node_types import NodeType
from app.studio.architecture.information_graph import StudioNodeType

# Local Studio Navigation Node Types
STUDIO_NAVIGATION_SYSTEM_NODE = "NAVIGATION_SYSTEM_NODE"
STUDIO_ROUTING_MODEL_NODE = "ROUTING_MODEL_NODE"
STUDIO_ROUTE_NODE = "ROUTE_NODE"
STUDIO_WORKFLOW_ROUTE_NODE = "WORKFLOW_ROUTE_NODE"
STUDIO_NAV_MENU_NODE = "NAV_MENU_NODE"
STUDIO_NAV_ITEM_NODE = "NAV_ITEM_NODE"

class NavigationGraph(ProjectTopologyGraph):
    """
    In-memory representation of routing models, menu structures, and page paths.
    This graph is framework-agnostic and remains abstract.
    """
    
    def __init__(self, **data: Any):
        super().__init__(**data)

    def add_node(self, node_id: str, node_type: Any, properties: Optional[Dict[str, Any]] = None) -> TopologyNode:
        """
        Override to allow local Studio navigation node types alongside application/information/intent types.
        Bypasses core Sentinel enum validation constraints.
        """
        studio_nav_types = (
            STUDIO_NAVIGATION_SYSTEM_NODE,
            STUDIO_ROUTING_MODEL_NODE,
            STUDIO_ROUTE_NODE,
            STUDIO_WORKFLOW_ROUTE_NODE,
            STUDIO_NAV_MENU_NODE,
            STUDIO_NAV_ITEM_NODE
        )
        
        is_studio_nav = str(node_type) in studio_nav_types
        is_sentinel_node = False
        try:
            is_sentinel_node = node_type in NodeType.__members__.values()
        except Exception:
            pass

        # Allow parents as references
        is_design_intent_type = str(node_type) in ("DESIGN_INTENT_NODE", "GLOBAL_INTENT_NODE", "PAGE_NODE")

        if not (is_studio_nav or is_sentinel_node or is_design_intent_type):
            raise ValueError(f"Invalid Node Type in NavigationGraph: {node_type}")

        # Construct TopologyNode using construct() to bypass strict Pydantic Enum validation if it's a Studio node type
        if is_studio_nav or is_design_intent_type:
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

    def add_navigation_node(self, node_id: str, node_type: str, properties: Optional[Dict[str, Any]] = None) -> None:
        """Helper to add only navigation domain nodes."""
        studio_nav_types = (
            STUDIO_NAVIGATION_SYSTEM_NODE,
            STUDIO_ROUTING_MODEL_NODE,
            STUDIO_ROUTE_NODE,
            STUDIO_WORKFLOW_ROUTE_NODE,
            STUDIO_NAV_MENU_NODE,
            STUDIO_NAV_ITEM_NODE
        )
        if node_type not in studio_nav_types:
            raise ValueError(f"Cannot add non-navigation-system node {node_type} to NavigationGraph.")
        
        self.add_node(node_id, node_type, properties)
