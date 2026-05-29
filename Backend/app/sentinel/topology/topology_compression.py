# app/sentinel/topology/topology_compression.py
"""
V4 Bounded Cognition — Phase 4: Meaning-Aware UI Compression

Actively compresses generic UI topologies (clustering, hierarchy folding, edge compression)
to prevent graph spaghetti, while preserving semantically distinct regions.
"""

from typing import List, Set, Dict, Any
from app.sentinel.topology.project_graph import ProjectTopologyGraph
from app.sentinel.topology.node_types import NodeType
from app.core.logging import log

class TopologyCompressor:
    """
    Meaning-aware compression engine for topological graphs.
    """

    # Semantic regions that MUST NOT be folded/compressed together
    SEMANTIC_PROTECTED_REGIONS = {"sidebar", "toolbar", "navbar", "filter", "header", "footer", "action_controls", "menu"}

    @classmethod
    def compress_topology(cls, graph: ProjectTopologyGraph) -> ProjectTopologyGraph:
        """
        Compresses redundant generic UI nodes into logical clusters.
        """
        log("COGNITION", "🗜️ Executing meaning-aware topology compression...")
        
        # We will track nodes to remove and edges to re-route
        nodes_to_remove: Set[str] = set()
        
        # 1. Identify purely generic structural containers
        # E.g., multiple nested generic views that have no distinct semantic role
        
        # Group generic views by their parent
        parent_to_generic_children: Dict[str, List[str]] = {}
        child_to_parent: Dict[str, str] = {}
        
        for edge in graph.edges:
            if edge.relation in ("contains", "renders"):
                child_to_parent[edge.target_id] = edge.source_id

        for node_id, node in graph.nodes.items():
            if node.node_type == NodeType.UI_NODE:
                role = str(node.properties.get("role", "")).lower()
                name = str(node.properties.get("component_name", "")).lower()
                
                # Check if it's protected
                is_protected = any(p in role for p in cls.SEMANTIC_PROTECTED_REGIONS) or \
                               any(p in name for p in cls.SEMANTIC_PROTECTED_REGIONS)
                
                if not is_protected and ("container" in role or "generic" in role or "view" in role):
                    parent_id = child_to_parent.get(node_id)
                    if parent_id:
                        if parent_id not in parent_to_generic_children:
                            parent_to_generic_children[parent_id] = []
                        parent_to_generic_children[parent_id].append(node_id)

        # 2. Hierarchy Folding: If a parent contains ONLY generic containers which themselves contain children,
        # we can fold the middle container.
        for parent_id, children in parent_to_generic_children.items():
            for child_id in children:
                # If child_id has its own children
                childs_children = [e.target_id for e in graph.edges if e.source_id == child_id and e.relation == "contains"]
                
                # If the child is purely a passthrough generic view, remove it and link parent to grandchildren
                if len(childs_children) > 0 and len(childs_children) < 3:
                    # Reroute edges
                    for grandchild in childs_children:
                        graph.add_edge(source_id=parent_id, target_id=grandchild, relation="contains")
                    
                    nodes_to_remove.add(child_id)

        # Apply removals
        if nodes_to_remove:
            log("COGNITION", f"🗜️ Compressed (folded) {len(nodes_to_remove)} generic UI nodes.")
            # Remove edges pointing to or from removed nodes
            new_edges = [e for e in graph.edges if e.source_id not in nodes_to_remove and e.target_id not in nodes_to_remove]
            graph.edges = new_edges
            
            for n_id in nodes_to_remove:
                del graph.nodes[n_id]
        else:
            log("COGNITION", "🗜️ No topological compression required. Density optimal.")

        return graph
