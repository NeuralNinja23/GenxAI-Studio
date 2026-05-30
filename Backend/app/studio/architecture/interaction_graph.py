# app/studio/architecture/interaction_graph.py
"""
V4 GenxAI Studio — Phase GS-8: InteractionGraph

Represents framework-agnostic interactive structures, triggers, transitions, state mutations,
and behavioral feedback loops decoupled from concrete rendering runtimes.
"""

from typing import Dict, Any, Optional
from app.sentinel.topology.project_graph import ProjectTopologyGraph, TopologyNode
from app.sentinel.topology.node_types import NodeType
from app.studio.architecture.information_graph import StudioNodeType

# Local Studio Interaction Node Types
STUDIO_INTERACTION_SYSTEM_NODE = "INTERACTION_SYSTEM_NODE"
STUDIO_INTERACTION_INTENT_NODE = "INTERACTION_INTENT_NODE"
STUDIO_INTERACTION_LOOP_NODE = "INTERACTION_LOOP_NODE"
STUDIO_TRIGGER_NODE = "TRIGGER_NODE"
STUDIO_TRANSITION_NODE = "TRANSITION_NODE"
STUDIO_MUTATION_NODE = "MUTATION_NODE"

class InteractionGraph(ProjectTopologyGraph):
    """
    In-memory representation of declarative triggers, state mutations, transition behaviors,
    and cognitive feedback loops.
    """
    
    def __init__(self, **data: Any):
        super().__init__(**data)

    def add_node(self, node_id: str, node_type: Any, properties: Optional[Dict[str, Any]] = None) -> TopologyNode:
        """
        Override to allow local Studio Interaction node types alongside application/information/intent types.
        Bypasses core Sentinel enum validation constraints.
        """
        studio_int_types = (
            STUDIO_INTERACTION_SYSTEM_NODE,
            STUDIO_INTERACTION_INTENT_NODE,
            STUDIO_INTERACTION_LOOP_NODE,
            STUDIO_TRIGGER_NODE,
            STUDIO_TRANSITION_NODE,
            STUDIO_MUTATION_NODE
        )
        
        is_studio_int = str(node_type) in studio_int_types
        is_sentinel_node = False
        try:
            is_sentinel_node = node_type in NodeType.__members__.values()
        except Exception:
            pass

        # Allow parents as references
        is_parent_type = str(node_type) in (
            "DESIGN_INTENT_NODE", "COMPONENT_NODE", "STATE_NODE", "TASK_FLOW_NODE"
        )

        if not (is_studio_int or is_sentinel_node or is_parent_type):
            raise ValueError(f"Invalid Node Type in InteractionGraph: {node_type}")

        # Construct TopologyNode using construct() to bypass strict Pydantic Enum validation if it's a Studio node type
        if is_studio_int or is_parent_type:
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

    def add_interaction_node(self, node_id: str, node_type: str, properties: Optional[Dict[str, Any]] = None) -> None:
        """Helper to add only Interaction domain nodes."""
        studio_int_types = (
            STUDIO_INTERACTION_SYSTEM_NODE,
            STUDIO_INTERACTION_INTENT_NODE,
            STUDIO_INTERACTION_LOOP_NODE,
            STUDIO_TRIGGER_NODE,
            STUDIO_TRANSITION_NODE,
            STUDIO_MUTATION_NODE
        )
        if node_type not in studio_int_types:
            raise ValueError(f"Cannot add non-interaction node {node_type} to InteractionGraph.")
        
        self.add_node(node_id, node_type, properties)
