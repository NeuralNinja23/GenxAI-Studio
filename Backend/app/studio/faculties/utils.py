# app/studio/faculties/utils.py
from app.sentinel.topology.project_graph import ProjectTopologyGraph

def serialize_graph_for_llm(graph: ProjectTopologyGraph) -> str:
    """Serializes ProjectTopologyGraph into human-readable logical components, stripping file paths/code."""
    lines = []
    lines.append("=== CURRENT ACTIVE TOPOLOGY ===")
    
    for node_id, node in graph.nodes.items():
        lines.append(f"- Node: {node_id} ({node.node_type.value})")
        props = node.properties
        if node.node_type.value == "SCHEMA_NODE":
            lines.append(f"  Entity Name: {props.get('entity_name')}")
            lines.append(f"  Description: {props.get('description')}")
            fields = props.get('fields', [])
            fields_str = ", ".join([f"{f['name']}: {f['type']}" for f in fields])
            lines.append(f"  Fields: [{fields_str}]")
        elif node.node_type.value == "API_NODE":
            lines.append(f"  Router Name: {props.get('router_name')}")
            endpoints = props.get('endpoints', [])
            eps_str = ", ".join([f"{e['method']} {e['path']}" for e in endpoints])
            lines.append(f"  Endpoints: [{eps_str}]")
        elif node.node_type.value == "UI_NODE":
            lines.append(f"  Component Name: {props.get('component_name')}")
            lines.append(f"  Layout Type: {props.get('layout_type')}")
            lines.append(f"  Role: {props.get('role')}")
            bindings = props.get('state_bindings', [])
            bindings_str = ", ".join([f"{b['state_name']} ({b['binding_type']})" for b in bindings])
            lines.append(f"  State Bindings: [{bindings_str}]")
            
    for edge in graph.edges:
        lines.append(f"- Relationship: {edge.source_id} ==[{edge.relation}]==> {edge.target_id}")
        
    return "\n".join(lines)
