# app/sentinel/cognition/experience_graph.py
"""
V4 Cognition Subsystem — Phase 7: Experience Graph

The Experience Graph is an internal, purely in-memory cognitive structure.
It models the user's intent as a hierarchy of Goals, Journeys, Flows, Screens, and Actions
BEFORE reasoning about concrete software components (UI/DATA topology).
"""

from typing import Dict, Any, Optional
from app.sentinel.topology.project_graph import ProjectTopologyGraph
from app.sentinel.topology.node_types import NodeType

class ExperienceGraph(ProjectTopologyGraph):
    """
    In-memory semantic model of user experience requirements.
    This graph is NOT projected to files. It acts as an intermediate
    cognition artifact that guides UI and Application Architecture Generation.
    
    Valid Node Types:
    - EXPERIENCE_NODE
    - GOAL_NODE
    - JOURNEY_NODE
    - FLOW_NODE
    - SCREEN_NODE
    - ACTION_NODE
    """
    
    def __init__(self, **data: Any):
        super().__init__(**data)

    def add_experience_node(self, node_id: str, node_type: NodeType, properties: Optional[Dict[str, Any]] = None) -> None:
        """Helper to add only experience domain nodes."""
        if node_type not in (
            NodeType.EXPERIENCE_NODE,
            NodeType.GOAL_NODE,
            NodeType.JOURNEY_NODE,
            NodeType.FLOW_NODE,
            NodeType.SCREEN_NODE,
            NodeType.ACTION_NODE
        ):
            raise ValueError(f"Cannot add non-experience node {node_type} to ExperienceGraph.")
        
        self.add_node(node_id, node_type, properties)
