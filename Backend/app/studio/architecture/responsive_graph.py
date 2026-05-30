# app/studio/architecture/responsive_graph.py
"""
V4 GenxAI Studio — Phase GS-9: ResponsiveGraph

Represents framework-agnostic responsive cognitive structures, viewports, responsive intents,
attention capacities, cognitive densities, interaction costs, priority rules, and layout overrides.
"""

from typing import Dict, Any, Optional
from app.sentinel.topology.project_graph import ProjectTopologyGraph, TopologyNode
from app.sentinel.topology.node_types import NodeType
from app.studio.architecture.information_graph import StudioNodeType

# Local Studio Responsive Node Types
STUDIO_RESPONSIVE_SYSTEM_NODE = "RESPONSIVE_SYSTEM_NODE"
STUDIO_RESPONSIVE_INTENT_NODE = "RESPONSIVE_INTENT_NODE"
STUDIO_VIEWPORT_CONSTRAINT_NODE = "VIEWPORT_CONSTRAINT_NODE"
STUDIO_ATTENTION_NODE = "ATTENTION_NODE"
STUDIO_DENSITY_NODE = "DENSITY_NODE"
STUDIO_INTERACTION_COST_NODE = "INTERACTION_COST_NODE"
STUDIO_PRIORITY_NODE = "PRIORITY_NODE"
STUDIO_ADAPTATION_RULE_NODE = "ADAPTATION_RULE_NODE"
STUDIO_LAYOUT_OVERRIDE_NODE = "LAYOUT_OVERRIDE_NODE"

class ResponsiveGraph(ProjectTopologyGraph):
    """
    In-memory representation of declarative viewports, responsive intents, attention scales,
    cognitive densities, interaction costs, and Priority-driven reflow overrides.
    """
    
    def __init__(self, **data: Any):
        super().__init__(**data)

    def add_node(self, node_id: str, node_type: Any, properties: Optional[Dict[str, Any]] = None) -> TopologyNode:
        """
        Override to allow local Studio Responsive node types alongside application/information/intent/interaction types.
        Bypasses core Sentinel enum validation constraints.
        """
        studio_resp_types = (
            STUDIO_RESPONSIVE_SYSTEM_NODE,
            STUDIO_RESPONSIVE_INTENT_NODE,
            STUDIO_VIEWPORT_CONSTRAINT_NODE,
            STUDIO_ATTENTION_NODE,
            STUDIO_DENSITY_NODE,
            STUDIO_INTERACTION_COST_NODE,
            STUDIO_PRIORITY_NODE,
            STUDIO_ADAPTATION_RULE_NODE,
            STUDIO_LAYOUT_OVERRIDE_NODE
        )
        
        is_studio_resp = str(node_type) in studio_resp_types
        is_sentinel_node = False
        try:
            is_sentinel_node = node_type in NodeType.__members__.values()
        except Exception:
            pass

        # Allow parents as references
        is_parent_type = str(node_type) in (
            "DESIGN_INTENT_NODE", "COMPONENT_NODE", "STATE_NODE", "TASK_FLOW_NODE",
            "INTERACTION_LOOP_NODE", "TRIGGER_NODE", "TRANSITION_NODE", "MUTATION_NODE",
            "LAYOUT_CONTAINER_NODE"
        )

        if not (is_studio_resp or is_sentinel_node or is_parent_type):
            raise ValueError(f"Invalid Node Type in ResponsiveGraph: {node_type}")

        # Construct TopologyNode using construct() to bypass strict Pydantic Enum validation if it's a Studio node type
        if is_studio_resp or is_parent_type:
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

    def add_responsive_node(self, node_id: str, node_type: str, properties: Optional[Dict[str, Any]] = None) -> None:
        """Helper to add only Responsive domain nodes."""
        studio_resp_types = (
            STUDIO_RESPONSIVE_SYSTEM_NODE,
            STUDIO_RESPONSIVE_INTENT_NODE,
            STUDIO_VIEWPORT_CONSTRAINT_NODE,
            STUDIO_ATTENTION_NODE,
            STUDIO_DENSITY_NODE,
            STUDIO_INTERACTION_COST_NODE,
            STUDIO_PRIORITY_NODE,
            STUDIO_ADAPTATION_RULE_NODE,
            STUDIO_LAYOUT_OVERRIDE_NODE
        )
        if node_type not in studio_resp_types:
            raise ValueError(f"Cannot add non-responsive node {node_type} to ResponsiveGraph.")
        
        self.add_node(node_id, node_type, properties)
