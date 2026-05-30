# Backend/tests/unit/test_verification_gate.py
"""
S-0.13 Automated Verification Gate Test Suite
Asserts structural physics, dynamic rollbacks, schema contract mismatches, 
and state handler validations.
"""

import os
import shutil
import pytest
import tempfile
from pathlib import Path

from app.sentinel.topology.node_types import NodeType
from app.sentinel.topology.project_graph import ProjectTopologyGraph
from app.sentinel.verification.verification_gate import SentinelVerificationGate, FailureFingerprint


@pytest.mark.asyncio
async def test_dependency_verification_gate():
    """Verify that Verification Layer A detects unresolved alias and relative imports."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_path = Path(tmp_dir)
        
        # Create mock directories
        components_dir = project_path / "Frontend" / "src" / "components"
        components_dir.mkdir(parents=True)
        
        # Write valid component file
        with open(components_dir / "Button.tsx", "w", encoding="utf-8") as f:
            f.write("export default function Button() { return <button>Click</button>; }")
            
        # Write invalid component with unresolved import
        with open(components_dir / "Dashboard.tsx", "w", encoding="utf-8") as f:
            f.write('import Button from "./Button";\nimport Missing from "@/components/MissingComponent";\n')

        graph = ProjectTopologyGraph(project_id="dep_test")
        graph.add_node("ui_dashboard", NodeType.UI_NODE)
        graph.update_graph_hash()

        res = SentinelVerificationGate.verify(project_path, graph)
        
        assert not res.dependency_passed
        assert res.dependency_survival < 1.0
        assert any(f.failure_type == "UNRESOLVED_IMPORT_FAILURE" for f in res.failures)
        assert any("MissingComponent" in f.details for f in res.failures)


@pytest.mark.asyncio
async def test_schema_contract_matching_gate():
    """Verify that Verification Layer B detects missing frontend field accesses."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_path = Path(tmp_dir)
        
        components_dir = project_path / "Frontend" / "src" / "components"
        components_dir.mkdir(parents=True)
        
        # UI Component references non-existent schema field `item.fullName`
        with open(components_dir / "UserManager.tsx", "w", encoding="utf-8") as f:
            f.write("const { fullName } = item;\nconst name = item.name;")

        graph = ProjectTopologyGraph(project_id="schema_test")
        graph.add_node("schema_user", NodeType.SCHEMA_NODE, {
            "entity_name": "User",
            "fields": [
                {"name": "name", "type": "str", "required": True},
                {"name": "email", "type": "str", "required": False}
            ]
        })
        graph.add_node("ui_usermanager", NodeType.UI_NODE)
        graph.update_graph_hash()

        res = SentinelVerificationGate.verify(project_path, graph)
        
        assert not res.schema_passed
        assert any(f.failure_type == "SCHEMA_CONTRACT_FAILURE" for f in res.failures)
        assert any("fullName" in f.details for f in res.failures)


@pytest.mark.asyncio
async def test_state_binding_tracing_gate():
    """Verify that Verification Layer C detects unresolved handlers for buttons and forms."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_path = Path(tmp_dir)
        
        components_dir = project_path / "Frontend" / "src" / "components"
        components_dir.mkdir(parents=True)
        
        # Component declares onClick handler but doesn't implement it
        with open(components_dir / "Form.tsx", "w", encoding="utf-8") as f:
            f.write("export default function Form() { return <button onClick={customSubmitHandler}>Submit</button>; }")

        graph = ProjectTopologyGraph(project_id="state_test")
        graph.add_node("ui_form", NodeType.UI_NODE)
        graph.update_graph_hash()

        res = SentinelVerificationGate.verify(project_path, graph)
        
        assert not res.state_binding_passed
        assert any(f.failure_type == "STATE_BINDING_FAILURE" for f in res.failures)


@pytest.mark.asyncio
async def test_topology_integrity_verification_gate():
    """Verify that Verification Layer F detects orphaned schemas and disjointed workflows."""
    graph = ProjectTopologyGraph(project_id="topo_integ_test")
    
    # Adding a schema node without any UI_NODE renders_component bindings or match
    graph.add_node("schema_isolated", NodeType.SCHEMA_NODE, {"entity_name": "Isolated"})
    graph.update_graph_hash()
    
    res = SentinelVerificationGate.verify(Path("."), graph)
    
    assert not res.topology_passed
    assert any(f.failure_type == "TOPOLOGY_INTEGRITY_FAILURE" for f in res.failures)
