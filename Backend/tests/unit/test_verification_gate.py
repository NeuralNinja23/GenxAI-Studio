# Backend/tests/unit/test_verification_gate.py
"""
S-0.13 Automated Verification Gate Test Suite
Asserts structural physics, dynamic rollbacks, schema contract mismatches, 
state handler validations, and Marcus V2 Governance Analyst grounding.
"""

import os
import shutil
import pytest
import tempfile
from pathlib import Path

from app.sentinel.topology.node_types import NodeType
from app.sentinel.topology.project_graph import ProjectTopologyGraph
from app.sentinel.verification.verification_gate import (
    FailureFingerprint,
    SentinelVerificationGate,
    VerificationResult,
    SentinelTopologyVerifier,
)


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
        graph.add_node("ui_dashboard", NodeType.UI_NODE, {"is_root": True})
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
        graph.add_node("ui_usermanager", NodeType.UI_NODE, {"is_root": True})
        graph.update_graph_hash()

        res = SentinelVerificationGate.verify(project_path, graph)
        
        assert res.schema_passed
        assert any(f.failure_type == "SCHEMA_CONTRACT_FAILURE" for f in res.warnings)
        assert any("fullName" in f.details for f in res.warnings)


@pytest.mark.asyncio
async def test_state_binding_tracing_gate():
    """Verify that Verification Layer C detects unresolved handlers for buttons and forms."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_path = Path(tmp_dir)

        components_dir = project_path / "Frontend" / "src" / "components"
        components_dir.mkdir(parents=True)

        # Component declares onClick handler but doesn't implement it
        with open(components_dir / "Form.tsx", "w", encoding="utf-8") as f:
            f.write(
                "export default function Form() { "
                "return <button onClick={customSubmitHandler}>Submit</button>; "
                "}"
            )

        graph = ProjectTopologyGraph(project_id="state_test")
        graph.add_node("ui_form", NodeType.UI_NODE, {"is_root": True})
        graph.update_graph_hash()

        res = SentinelVerificationGate.verify(project_path, graph)

        assert res.state_binding_passed

        # New S-0.4 taxonomy
        assert any(
            f.failure_type == "UNRESOLVED_EVENT_HANDLER"
            for f in res.warnings
        )

        assert any(
            "customSubmitHandler" in f.details
            for f in res.warnings
        )


def _run_state_binding_gate(project_path: Path, graph: ProjectTopologyGraph) -> VerificationResult:
    result = VerificationResult()
    SentinelVerificationGate._verify_state_bindings(project_path, graph, result)
    return result


def test_state_binding_detects_handler_without_mutation():
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_path = Path(tmp_dir)
        components_dir = project_path / "Frontend" / "src" / "components"
        components_dir.mkdir(parents=True)

        with open(components_dir / "TaskPanel.tsx", "w", encoding="utf-8") as f:
            f.write(
                """
                export default function TaskPanel() {
                    const handleSave = () => { console.log("save"); };
                    return <button onClick={handleSave}>Save</button>;
                }
                """
            )

        graph = ProjectTopologyGraph(project_id="missing_mutation")
        graph.add_node("schema_task", NodeType.SCHEMA_NODE, {"entity_name": "Task"})

        res = _run_state_binding_gate(project_path, graph)

        assert res.state_binding_passed
        assert any(f.failure_type == "STATE_MUTATION_MISSING" for f in res.warnings)


def test_state_binding_detects_invalid_state_target_domain():
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_path = Path(tmp_dir)
        components_dir = project_path / "Frontend" / "src" / "components"
        components_dir.mkdir(parents=True)

        with open(components_dir / "TaskPanel.tsx", "w", encoding="utf-8") as f:
            f.write(
                """
                export default function TaskPanel() {
                    const [projects, setProjects] = useState([]);
                    const handleSave = () => { setProjects([...projects]); };
                    return <button onClick={handleSave}>Save</button>;
                }
                """
            )

        graph = ProjectTopologyGraph(project_id="invalid_target")
        graph.add_node("schema_task", NodeType.SCHEMA_NODE, {"entity_name": "Task"})
        graph.add_node("schema_project", NodeType.SCHEMA_NODE, {"entity_name": "Project"})

        res = _run_state_binding_gate(project_path, graph)

        assert res.state_binding_passed
        assert any(f.failure_type == "INVALID_STATE_TARGET" for f in res.warnings)


def test_state_binding_detects_orphaned_state_mutation():
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_path = Path(tmp_dir)
        components_dir = project_path / "Frontend" / "src" / "components"
        components_dir.mkdir(parents=True)

        with open(components_dir / "TaskPanel.tsx", "w", encoding="utf-8") as f:
            f.write(
                """
                export default function TaskPanel() {
                    const [tasks, setTasks] = useState([]);
                    const handleSave = () => { setTasks([{ id: 1 }]); };
                    return <button onClick={handleSave}>Save</button>;
                }
                """
            )

        graph = ProjectTopologyGraph(project_id="orphaned_state")
        graph.add_node("schema_task", NodeType.SCHEMA_NODE, {"entity_name": "Task"})

        res = _run_state_binding_gate(project_path, graph)

        assert res.state_binding_passed
        assert any(f.failure_type == "ORPHANED_STATE_MUTATION" for f in res.warnings)


def test_state_binding_resolves_imported_handler_mutation():
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_path = Path(tmp_dir)
        components_dir = project_path / "Frontend" / "src" / "components"
        components_dir.mkdir(parents=True)

        with open(components_dir / "TaskPanel.tsx", "w", encoding="utf-8") as f:
            f.write(
                """
                import { submitTask } from "./taskActions";
                export default function TaskPanel() {
                    return <button onClick={submitTask}>Save</button>;
                }
                """
            )
        with open(components_dir / "taskActions.ts", "w", encoding="utf-8") as f:
            f.write("export function submitTask() { return fetch('/api/tasks', { method: 'POST' }); }")

        graph = ProjectTopologyGraph(project_id="imported_handler")
        graph.add_node("schema_task", NodeType.SCHEMA_NODE, {"entity_name": "Task"})

        res = _run_state_binding_gate(project_path, graph)

        assert res.state_binding_passed
        assert not res.failures


def test_state_binding_resolves_visible_prop_drilled_handler():
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_path = Path(tmp_dir)
        components_dir = project_path / "Frontend" / "src" / "components"
        components_dir.mkdir(parents=True)

        with open(components_dir / "TaskButton.tsx", "w", encoding="utf-8") as f:
            f.write(
                """
                export function TaskButton({ onSave }) {
                    return <button onClick={onSave}>Save</button>;
                }
                """
            )
        with open(components_dir / "TaskPanel.tsx", "w", encoding="utf-8") as f:
            f.write(
                """
                import { TaskButton } from "./TaskButton";
                export default function TaskPanel() {
                    const [tasks, setTasks] = useState([]);
                    const handleSave = () => { setTasks([...tasks, { id: 1 }]); };
                    return <section>{tasks.map(task => task.id)}<TaskButton onSave={handleSave} /></section>;
                }
                """
            )

        graph = ProjectTopologyGraph(project_id="prop_drilled_handler")
        graph.add_node("schema_task", NodeType.SCHEMA_NODE, {"entity_name": "Task"})

        res = _run_state_binding_gate(project_path, graph)

        assert res.state_binding_passed
        assert not res.failures


@pytest.mark.asyncio
async def test_build_dry_run_failure():
    """
    Verify that Tier 0 compiler unavailability is detected when package.json/node_modules are missing.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_path = Path(tmp_dir)

        components_dir = project_path / "Frontend" / "src" / "components"
        components_dir.mkdir(parents=True)

        graph = ProjectTopologyGraph(project_id="build_test")
        graph.add_node("ui_brokencomponent", NodeType.UI_NODE)
        graph.update_graph_hash()

        res = SentinelVerificationGate.verify(project_path, graph)

        assert any(
            f.failure_type == "COMPILER_UNAVAILABLE"
            for f in res.failures
        )


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


@pytest.mark.asyncio
async def test_backend_build_failure():
    """
    Verify that Verification Layer D detects Python syntax failures.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_path = Path(tmp_dir)

        backend_dir = project_path / "Backend"
        backend_dir.mkdir(parents=True)

        with open(backend_dir / "broken.py", "w", encoding="utf-8") as f:
            f.write(
                """
def broken_function(
    print("missing closing parenthesis")
                """
            )

        graph = ProjectTopologyGraph(project_id="backend_build_test")
        graph.update_graph_hash()

        res = SentinelVerificationGate.verify(project_path, graph)

        assert not res.build_passed

        assert any(
            f.failure_type == "BACKEND_BUILD_FAILURE"
            for f in res.failures
        )


def test_build_dry_run_detects_unresolved_frontend_import():
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_path = Path(tmp_dir)
        components_dir = project_path / "Frontend" / "src" / "components"
        components_dir.mkdir(parents=True)

        with open(components_dir / "Dashboard.tsx", "w", encoding="utf-8") as f:
            f.write(
                """
                import MissingWidget from "./MissingWidget";
                export default function Dashboard() {
                    return <main><MissingWidget /></main>;
                }
                """
            )

        graph = ProjectTopologyGraph(project_id="frontend_import_build")
        result = VerificationResult()

        SentinelVerificationGate._verify_builds(project_path, graph, result)

        assert not result.build_passed
        assert any("Unresolved frontend import" in f.details for f in result.warnings)


def test_runtime_render_accepts_nonblank_app_with_router():
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_path = Path(tmp_dir)
        src_dir = project_path / "Frontend" / "src"
        src_dir.mkdir(parents=True)

        with open(src_dir / "App.tsx", "w", encoding="utf-8") as f:
            f.write(
                """
                import { BrowserRouter, Routes, Route } from "react-router-dom";
                export default function App() {
                    return (
                        <BrowserRouter>
                            <Routes>
                                <Route path="/" element={<main>Home</main>} />
                            </Routes>
                        </BrowserRouter>
                    );
                }
                """
            )

        result = VerificationResult()
        SentinelVerificationGate._verify_runtime_render(project_path, ProjectTopologyGraph(project_id="runtime_ok"), result)

        assert result.runtime_passed
        assert result.visual_passed


def test_runtime_render_detects_routes_without_router():
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_path = Path(tmp_dir)
        src_dir = project_path / "Frontend" / "src"
        src_dir.mkdir(parents=True)

        with open(src_dir / "App.tsx", "w", encoding="utf-8") as f:
            f.write(
                """
                import { Routes, Route } from "react-router-dom";
                export default function App() {
                    return <Routes><Route path="/" element={<main>Home</main>} /></Routes>;
                }
                """
            )

        result = VerificationResult()
        SentinelVerificationGate._verify_runtime_render(project_path, ProjectTopologyGraph(project_id="runtime_bad_router"), result)

        assert result.runtime_passed
        assert not result.visual_passed
        assert any(f.failure_type == "VISUAL_RENDER_FAILURE" for f in result.failures)


def test_topology_integrity_accepts_connected_projection():
    graph = ProjectTopologyGraph(project_id="topology_valid")
    graph.add_node("ui_app_root", NodeType.UI_NODE, {"is_root": True})
    graph.add_node("ui_task_panel", NodeType.UI_NODE)
    graph.add_node("schema_task", NodeType.SCHEMA_NODE, {"entity_name": "Task"})
    graph.add_edge("ui_app_root", "ui_task_panel", "renders_component")
    graph.add_edge("ui_task_panel", "schema_task", "binds_schema")

    result = VerificationResult()
    SentinelVerificationGate._verify_topology_integrity(graph, result)

    assert result.topology_passed
    assert result.topology_survival == 1.0


def test_topology_integrity_detects_structural_cycle():
    graph = ProjectTopologyGraph(project_id="topology_cycle")
    graph.add_node("ui_app_root", NodeType.UI_NODE, {"is_root": True})
    graph.add_node("ui_task_panel", NodeType.UI_NODE)
    graph.add_edge("ui_app_root", "ui_task_panel", "imports")
    graph.add_edge("ui_task_panel", "ui_app_root", "imports")

    result = VerificationResult()
    SentinelVerificationGate._verify_topology_integrity(graph, result)

    assert not result.topology_passed
    assert any("Cycle detected" in f.details for f in result.failures)


def test_topology_integrity_checks_intent_graph_expectations():
    graph = ProjectTopologyGraph(project_id="topology_actual")
    graph.add_node("ui_app_root", NodeType.UI_NODE, {"is_root": True})

    intent_graph = ProjectTopologyGraph(project_id="topology_intent")
    intent_graph.add_node("ui_app_root", NodeType.UI_NODE, {"is_root": True})
    intent_graph.add_node("ui_missing_panel", NodeType.UI_NODE)
    intent_graph.add_edge("ui_app_root", "ui_missing_panel", "renders_component")

    result = VerificationResult()
    SentinelVerificationGate._verify_topology_integrity(graph, result, intent_graph)

    assert not result.topology_passed
    assert any("Intent graph expected node" in f.details for f in result.failures)



# ─────────────────────────────────────────────────────────────
# S-0.13: Atomic Projector Rollback Behavior
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_atomic_projector_rollback_on_failure():
    """
    Simulates the ASTProjector's staging and atomic commit process.
    Ensures that if SentinelVerificationGate rejects the code, the 
    staging directory is wiped (rollback) and never committed to the main branch.
    """
    with tempfile.TemporaryDirectory() as main_repo_dir:
        main_repo_path = Path(main_repo_dir)
        
        # 1. Simulate AST Projector creating a staging branch/directory
        staging_dir = main_repo_path / ".sentinel_staging"
        staging_dir.mkdir()
        
        components_dir = staging_dir / "Frontend" / "src" / "components"
        components_dir.mkdir(parents=True)
        
        # 2. Write structurally invalid code to the staging directory
        invalid_file_path = components_dir / "SyntaxErrorComponent.tsx"
        with open(invalid_file_path, "w", encoding="utf-8") as f:
            f.write("export default function Bad() { return <div>Missing closure;")
            
        graph = ProjectTopologyGraph(project_id="rollback_test")
        graph.add_node("ui_bad", NodeType.UI_NODE)
        graph.update_graph_hash()

        # 3. Pass the STAGING directory to the Verification Gate
        res = SentinelVerificationGate.verify(staging_dir, graph)

        # 4. AST Projector Logic: Commit if PASS, Rollback if REJECT
        if res.recommendation == "REJECT":
            # Simulate Rollback: Wipe the staging directory
            shutil.rmtree(staging_dir)
            commit_successful = False
        else:
            # Simulate Commit: Move staging to main branch
            commit_successful = True

        # 5. Assertions: Prove the system protected the main branch
        assert res.recommendation == "REJECT"
        assert any(f.failure_type == "COMPILER_UNAVAILABLE" for f in res.failures)
        assert commit_successful is False
        assert not staging_dir.exists(), "CRITICAL: Staging directory was not rolled back after Sentinel rejection!"
        assert not (main_repo_path / "Frontend").exists(), "CRITICAL: Bad code leaked into the main repository!"


@pytest.mark.asyncio
async def test_sentinel_topology_verifier():
    """Verify that SentinelTopologyVerifier correctly validates in-memory graphs without file access."""
    graph = ProjectTopologyGraph(project_id="sentinel_test")
    
    # 1. Invalid Topology (missing entry route and state bindings)
    graph.add_node("ui_dash", NodeType.UI_NODE, {"is_root": False})
    graph.update_graph_hash()
    
    res = SentinelTopologyVerifier.verify(graph)
    assert not res.route_passed
    assert not res.state_passed
    assert res.verification_score < 0.5
    
    # 2. Perfect, valid topology
    valid_graph = ProjectTopologyGraph(project_id="sentinel_perfect")
    valid_graph.add_node("ui_perfect_root", NodeType.UI_NODE, {"is_root": True})
    valid_graph.add_node("state_perfect_root", NodeType.STATE_NODE)
    valid_graph.add_edge(source_id="ui_perfect_root", target_id="state_perfect_root", relation="binds_state")
    valid_graph.update_graph_hash()
    
    perfect_res = SentinelTopologyVerifier.verify(valid_graph)
    assert perfect_res.route_passed
    assert perfect_res.state_passed
    assert perfect_res.topology_passed
    assert perfect_res.schema_passed
    assert perfect_res.dependency_graph_passed
    assert perfect_res.verification_score == 1.0