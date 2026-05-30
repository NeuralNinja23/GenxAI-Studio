# app/studio/architecture/application_graph.py
"""
V4 GenxAI Studio — Phase GS-1: ApplicationGraph

The Application Graph is a purely in-memory structural representation of the application structure,
layout, page hierarchy, feature nodes, and workspaces.
"""

from typing import Dict, Any, Optional
from app.sentinel.topology.project_graph import ProjectTopologyGraph
from app.sentinel.topology.node_types import NodeType

class ApplicationGraph(ProjectTopologyGraph):
    """
    In-memory representation of application page architecture, features, and layouts.
    This graph remains abstract and is NOT projected directly to frontend code files.
    
    Valid Node Types:
    - WORKSPACE_NODE
    - PAGE_NODE
    - FEATURE_NODE
    - NAV_LAYOUT_NODE
    """
    
    def __init__(self, **data: Any):
        super().__init__(**data)

    def add_application_node(self, node_id: str, node_type: NodeType, properties: Optional[Dict[str, Any]] = None) -> None:
        """Helper to add only application domain nodes."""
        if node_type not in (
            NodeType.WORKSPACE_NODE,
            NodeType.PAGE_NODE,
            NodeType.FEATURE_NODE,
            NodeType.NAV_LAYOUT_NODE
        ):
            raise ValueError(f"Cannot add non-application node {node_type} to ApplicationGraph.")
        
        self.add_node(node_id, node_type, properties)
