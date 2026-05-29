# tests/unit/test_topology.py
"""
V4 Topology Engine Unit Tests — Stage 2: Canonical Topology Engine
"""

import pytest
import tempfile
import json
import asyncio
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock

from app.models.runtime_models import MutationTier, TransactionStatus
from app.models.directive import IntentField, DomainEntity, DomainEntityField, SemanticConstraint, WorkflowLegalityRule
from app.sentinel.topology.node_types import NodeType, NodeOntology
from app.sentinel.topology.project_graph import ProjectTopologyGraph
from app.sentinel.topology.topology_compiler import TopologyCompiler
from app.sentinel.topology.topology_validator import TopologyValidator
from app.sentinel.topology.structural_diff import StructuralDiff
from app.sentinel.topology.topology_builder import TopologyBuilder
from app.sentinel.topology.topology_version_manager import TopologyVersionManager, TopologyVersionRecord

@pytest.fixture(scope="session", autouse=True)
def init_beanie_mock():
    """Mock Beanie ODM collection getter so documents can be instantiated without direct DB connection."""
    IntentField.get_pymongo_collection = MagicMock()
    TopologyVersionRecord.get_pymongo_collection = MagicMock()
    TopologyVersionRecord.find_one = AsyncMock(return_value=None)
    TopologyVersionRecord.insert = AsyncMock()


@pytest.mark.asyncio
async def test_node_ontology():
    """Verify that node types carry strict classification, boundaries, and tiers."""
    assert NodeOntology.get_max_mutation_tier(NodeType.UI_NODE) == MutationTier.STRUCTURAL_UI
    assert NodeOntology.get_max_mutation_tier(NodeType.SCHEMA_NODE) == MutationTier.TOPOLOGY
    assert NodeOntology.get_max_mutation_tier(NodeType.RUNTIME_NODE) == MutationTier.FORBIDDEN

    boundary = NodeOntology.get_boundary(NodeType.API_NODE)
    assert "Victoria" in boundary.allowed_proposers
    assert "Derek" in boundary.allowed_proposers
    assert "Luna" in boundary.allowed_validators

    proj = NodeOntology.get_projection(NodeType.UI_NODE)
    assert "Frontend/src/components/**/*.tsx" in proj.allowed_file_patterns
    assert proj.target_format == "typescript"


@pytest.mark.asyncio
async def test_project_graph_integrity_and_hashing():
    """Verify that ProjectTopologyGraph deterministically calculates and verifies integrity hashes."""
    graph = ProjectTopologyGraph(project_id="test_proj")
    
    # Add nodes
    n1 = graph.add_node("schema_user", NodeType.SCHEMA_NODE, {"entity_name": "User"})
    n2 = graph.add_node("api_user", NodeType.API_NODE, {"endpoint": "/api/users"})
    
    assert n1.integrity_hash != ""
    assert n2.integrity_hash != ""
    assert graph.graph_hash != ""
    
    first_hash = graph.graph_hash

    # Add edge
    graph.add_edge("api_user", "schema_user", "binds_schema")
    assert graph.graph_hash != first_hash

    # Serialization and deserialization parity
    serialized = graph.serialize()
    deserialized = ProjectTopologyGraph.deserialize(serialized)
    assert deserialized.graph_hash == graph.graph_hash
    assert len(deserialized.nodes) == len(graph.nodes)


@pytest.mark.asyncio
async def test_topology_validator_cycles_and_edges():
    """Verify the structural physics engine identifies cyclic references and illegal connections."""
    graph = ProjectTopologyGraph(project_id="cycle_test")
    
    n1 = graph.add_node("service_user", NodeType.SERVICE_NODE)
    n2 = graph.add_node("api_user", NodeType.API_NODE)
    
    # 1. Illegal UI to Schema edge validation
    ui_node = graph.add_node("ui_dashboard", NodeType.UI_NODE)
    schema_node = graph.add_node("schema_user", NodeType.SCHEMA_NODE)
    graph.add_edge("ui_dashboard", "schema_user", "imports")  # Directly connecting UI to Schema
    
    result = TopologyValidator.validate_graph(graph)
    assert not result.passed
    assert any(v.rule == "ILLEGAL_UI_TO_SCHEMA_EDGE" for v in result.violations)

    # Clean the illegal edge
    graph.remove_edge("ui_dashboard", "schema_user", "imports")

    # 2. Cycle detection: Service -> API -> Service
    graph.add_edge("service_user", "api_user", "depends_on")
    graph.add_edge("api_user", "service_user", "depends_on")

    result = TopologyValidator.validate_graph(graph)
    assert not result.passed
    assert any("CYCLIC" in v.rule for v in result.violations)


@pytest.mark.asyncio
async def test_structural_diff_and_convergence():
    """Verify semantic differential analysis, mutation classification, and convergence scoring."""
    base_graph = ProjectTopologyGraph(project_id="diff_test")
    base_graph.add_node("schema_task", NodeType.SCHEMA_NODE, {"entity": "Task"})
    base_graph.add_node("api_task", NodeType.API_NODE, {"route": "/tasks"})
    base_graph.add_edge("api_task", "schema_task", "depends_on")
    base_graph.update_graph_hash()

    # Create mutated target graph
    target_graph = ProjectTopologyGraph(project_id="diff_test")
    target_graph.add_node("schema_task", NodeType.SCHEMA_NODE, {"entity": "Task"})
    target_graph.add_node("api_task", NodeType.API_NODE, {"route": "/tasks"})
    
    # Mutate 1: Add a cosmetic node
    target_graph.add_node("ui_button", NodeType.UI_NODE, {"color": "blue"})
    # Mutate 2: Change base edge
    target_graph.add_edge("api_task", "schema_task", "depends_on")
    target_graph.add_edge("ui_button", "api_task", "calls_api")
    target_graph.update_graph_hash()

    diff = StructuralDiff.compare(base_graph, target_graph)
    
    # Verify diff captures node additions
    assert len(diff.nodes_changed) == 1
    assert diff.nodes_changed[0].node_id == "ui_button"
    assert diff.nodes_changed[0].change_type == "added"
    
    # Verify tier classification (UI node addition maps to Tier 2 Structural UI)
    assert diff.max_mutation_tier == MutationTier.STRUCTURAL_UI
    
    # Verify convergence score is below 1.0 (some divergence occurred)
    assert diff.convergence_score < 1.0
    assert diff.convergence_score > 0.0


@pytest.mark.asyncio
async def test_topology_compiler():
    """Verify that IntentField boundaries compile correctly into a legal topology graph."""
    intent = IntentField(
        project_id="compiled_proj",
        ux_intent={"archetype": "dashboard"},
        invariants=["auth_required"],
        constraints=[SemanticConstraint(rule_id="sec-1", description="No auth bypass", validation_target="API")],
        workflow_legality=[WorkflowLegalityRule(workflow_id="wf-login", allowed_transitions=["login", "dashboard"])],
        domain_entities=[
            DomainEntity(
                name="Project",
                description="Project model",
                fields=[DomainEntityField(name="name", type="str", required=True)]
            )
        ]
    )

    graph = TopologyCompiler.compile_intent(project_id="compiled_proj", intent=intent)

    # Check compiled nodes
    assert "sys_contract_boundary" in graph.nodes
    assert "schema_project" in graph.nodes
    assert "api_project" in graph.nodes
    assert "ui_layout_root" in graph.nodes
    assert "workflow_wf-login" in graph.nodes

    # Check compiled edges
    assert len(graph.edges) > 0
    assert any(e.source_id == "ui_layout_root" and e.target_id == "ui_component_project" for e in graph.edges)
    
    # Deterministic validate passes on compiler output
    val_result = TopologyValidator.validate_graph(graph)
    assert val_result.passed


@pytest.mark.asyncio
async def test_topology_builder_manifest_and_fallback():
    """Verify AST-first manifest parsing and filesystem-last fallback reconstruction."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        proj_path = Path(tmp_dir)
        project_id = "builder_test"

        # 1. AST-First: Create a valid .genx_ast_manifest.json
        manifest_path = proj_path / ".genx_ast_manifest.json"
        
        saved_graph = ProjectTopologyGraph(project_id=project_id)
        saved_graph.add_node("schema_dummy", NodeType.SCHEMA_NODE)
        saved_graph.update_graph_hash()

        manifest_data = {
            "project_id": project_id,
            "topology": saved_graph.serialize()
        }

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f)

        # Reconstruct must pick up AST manifest
        reconstructed = await TopologyBuilder.reconstruct(project_id, proj_path)
        assert "schema_dummy" in reconstructed.nodes
        assert reconstructed.graph_hash == saved_graph.graph_hash

        # 2. Filesystem Fallback: Delete manifest and mock project directories
        manifest_path.unlink()
        
        backend_app = proj_path / "Backend" / "app"
        (backend_app / "models").mkdir(parents=True)
        (backend_app / "api").mkdir(parents=True)
        
        # Write dummy files
        with open(backend_app / "models" / "item.py", "w", encoding="utf-8") as f:
            f.write("# Dummy schema\nclass Item:\n    pass\n")

        with open(backend_app / "api" / "item.py", "w", encoding="utf-8") as f:
            f.write("# Dummy API\nfrom Backend.app.models.item import Item\n")

        fallback_reconstructed = await TopologyBuilder.reconstruct(project_id, proj_path)
        
        # Verify scanner found dummy schema and API nodes
        assert "schema_item" in fallback_reconstructed.nodes
        assert "api_item" in fallback_reconstructed.nodes
        assert "route_item" in fallback_reconstructed.nodes
        
        # Re-established manifest check
        assert manifest_path.exists()


@pytest.mark.asyncio
async def test_ast_generation():
    """Verify that ASTGenerator synthesizes structured ASTFile configurations correctly."""
    from app.sentinel.topology.ast_generator import ASTGenerator
    
    graph = ProjectTopologyGraph(project_id="ast_gen_test")
    graph.add_node("schema_todo", NodeType.SCHEMA_NODE, {
        "entity_name": "Todo",
        "fields": [{"name": "title", "type": "str", "required": True}]
    })
    graph.update_graph_hash()

    ast_files = ASTGenerator.generate(graph)
    
    # 1. Verify schema class generation
    schema_path = "Backend/app/models/runtime_models.py"
    assert schema_path in ast_files
    
    af = ast_files[schema_path]
    assert len(af.classes) == 1
    assert af.classes[0].name == "Todo"
    assert len(af.classes[0].fields) == 1
    assert af.classes[0].fields[0].name == "title"
    
    # Verify Pydantic/Beanie imports
    assert any(imp.source == "beanie" for imp in af.imports)
    assert any(imp.source == "pydantic" for imp in af.imports)


@pytest.mark.asyncio
async def test_ast_mutator_surgical():
    """Verify ASTMutator executes controlled scope-aware and node-aware structural mutations."""
    from app.sentinel.topology.ast_generator import ASTFile, ASTClass, ASTMethod
    from app.sentinel.topology.ast_mutator import ASTMutator

    af = ASTFile(file_path="Backend/app/api/todos.py")
    af.classes.append(ASTClass(name="TodoRouter"))
    af.update_integrity()

    # 1. Surgical Import Addition
    ASTMutator.add_import(af, "fastapi", ["APIRouter"])
    assert len(af.imports) == 1
    assert af.imports[0].source == "fastapi"
    assert "APIRouter" in af.imports[0].symbols

    # 2. Add class method
    method = ASTMethod(name="get_todos", args=["request"], body=["return []"], return_type="list")
    ASTMutator.add_class_method(af, "TodoRouter", method)
    
    assert len(af.classes[0].methods) == 1
    assert af.classes[0].methods[0].name == "get_todos"
    assert "return []" in af.classes[0].methods[0].body


@pytest.mark.asyncio
async def test_ast_merging():
    """Verify ASTMerger reconciles syntax trees deterministically without string manipulation."""
    from app.sentinel.topology.ast_generator import ASTFile, ASTClass, ASTField
    from app.sentinel.topology.ast_merger import ASTMerger

    base = ASTFile(file_path="Backend/app/models/runtime_models.py")
    base.classes.append(ASTClass(name="Todo", fields=[ASTField(name="title", type_str="str")]))
    base.update_integrity()

    target = ASTFile(file_path="Backend/app/models/runtime_models.py")
    target.classes.append(ASTClass(name="Todo", fields=[ASTField(name="done", type_str="bool")]))
    target.update_integrity()

    # Merge target into base
    merged = ASTMerger.merge(base, target)
    
    # Asserts deduplicated and aggregated fields inside the Todo class
    assert len(merged.classes) == 1
    assert merged.classes[0].name == "Todo"
    
    field_names = [f.name for f in merged.classes[0].fields]
    assert "title" in field_names
    assert "done" in field_names


@pytest.mark.asyncio
async def test_ast_validation_physics():
    """Verify ASTValidator enforces syntax correctness, balanced tags, and projection limits."""
    from app.sentinel.topology.ast_generator import ASTFile, ASTImport
    from app.sentinel.topology.ast_validator import ASTValidator

    # 1. Valid Python compilation check
    valid_py = ASTFile(file_path="Backend/app/routers/health.py", raw_blocks=["def get_status():\n    return 'ok'"])
    valid_py.update_integrity()
    assert ASTValidator.validate_file(valid_py)["passed"]

    # 2. Invalid Python compilation check
    invalid_py = ASTFile(file_path="Backend/app/routers/health.py", raw_blocks=["def broken_syntax(:\n    pass"])
    invalid_py.update_integrity()
    assert not ASTValidator.validate_file(invalid_py)["passed"]

    # 3. TSX/JSX brackets mismatch check
    unbalanced_tsx = ASTFile(file_path="Frontend/src/components/Comp.tsx", raw_blocks=["export default function Comp() {\n  return (\n    <div>{unclosed\n  );\n}"])
    unbalanced_tsx.update_integrity()
    assert not ASTValidator.validate_file(unbalanced_tsx)["passed"]

    # 4. Forbidden write target check
    forbidden_write = ASTFile(file_path="Backend/requirements.txt", raw_blocks=["beanie==0.1.0"])
    forbidden_write.update_integrity()
    assert not ASTValidator.validate_file(forbidden_write)["passed"]


@pytest.mark.asyncio
async def test_ast_projector_flow():
    """Verify ASTProjector coordinates structural projection and updates active manifest json."""
    from app.sentinel.topology.ast_projector import ASTProjector
    from app.sentinel.topology.topology_version_manager import TopologyVersionManager

    with tempfile.TemporaryDirectory() as tmp_dir:
        proj_path = Path(tmp_dir)
        project_id = "projector_test"

        # Mock cycle context
        class MockCycleContext:
            def __init__(self, pid, ppath):
                self.project_id = pid
                self.project_path = ppath

        ctx = MockCycleContext(project_id, proj_path)

        # Define graph representing canonical topology state
        graph = ProjectTopologyGraph(project_id=project_id)
        graph.add_node("schema_task", NodeType.SCHEMA_NODE, {
            "entity_name": "Task",
            "fields": [{"name": "name", "type": "str", "required": True}]
        })
        graph.update_graph_hash()

        # Mock TopologyVersionManager to return the topology graph without making real DB queries
        from unittest.mock import AsyncMock
        TopologyVersionManager.get_active_topology = AsyncMock(return_value=graph)

        # Project topology to temporary filesystem directory
        res = await ASTProjector.project(ctx)
        
        # Verify projected files are generated safely
        assert "Backend/app/models/runtime_models.py" in res["files_written"]
        assert (proj_path / "Backend/app/models/runtime_models.py").exists()
        assert (proj_path / ".genx_ast_manifest.json").exists()


@pytest.mark.asyncio
async def test_syntax_oracle_physics():
    """Verify that SyntaxOracle evaluates physical syntax compilability correctly."""
    from app.sentinel.oracles.syntax_oracle import SyntaxOracle

    with tempfile.TemporaryDirectory() as tmp_dir:
        proj_path = Path(tmp_dir)
        project_id = "syntax_oracle_test"

        # Mock projection context listing generated files
        class MockContext:
            def __init__(self, files):
                self.files_written = files

        ctx = MockContext(["Backend/app/models/item.py"])

        # Create subdirectories and file on disk
        (proj_path / "Backend/app/models").mkdir(parents=True)
        with open(proj_path / "Backend/app/models/item.py", "w", encoding="utf-8") as f:
            f.write("class Item:\n    pass\n")

        oracle = SyntaxOracle()
        res = await oracle.validate(project_id, proj_path, ctx)
        
        assert res.passed
        assert "compiled" in res.reason
        assert res.evidence_key.startswith("ev-syntax-pass-")


@pytest.mark.asyncio
async def test_topology_oracle_consistency():
    """Verify that TopologyOracle verifies ProjectTopologyGraph and manifest congruence."""
    from app.sentinel.oracles.topology_oracle import TopologyOracle
    from app.sentinel.topology.topology_version_manager import TopologyVersionManager

    with tempfile.TemporaryDirectory() as tmp_dir:
        proj_path = Path(tmp_dir)
        project_id = "topology_oracle_test"

        graph = ProjectTopologyGraph(project_id=project_id)
        graph.add_node("schema_task", NodeType.SCHEMA_NODE)
        graph.update_graph_hash()

        from unittest.mock import AsyncMock
        TopologyVersionManager.get_active_topology = AsyncMock(return_value=graph)

        # Write manifest file aligning with active topology graph hash
        manifest_path = proj_path / ".genx_ast_manifest.json"
        manifest_data = {
            "project_id": project_id,
            "topology": graph.serialize()
        }
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f)

        oracle = TopologyOracle()
        res = await oracle.validate(project_id, proj_path, None)
        
        assert res.passed
        assert "aligned" in res.reason.lower()


@pytest.mark.asyncio
async def test_behavioral_oracle_coherence():
    """Verify that BehavioralOracle identifies orphaned elements and checks path coverage."""
    from app.sentinel.oracles.behavioral_oracle import BehavioralOracle
    from app.sentinel.topology.topology_version_manager import TopologyVersionManager

    project_id = "behavioral_oracle_test"
    graph = ProjectTopologyGraph(project_id=project_id)
    
    # Add an orphaned Schema node without a binds_schema edge from any Service node
    graph.add_node("schema_orphan", NodeType.SCHEMA_NODE)
    graph.update_graph_hash()

    from unittest.mock import AsyncMock
    TopologyVersionManager.get_active_topology = AsyncMock(return_value=graph)

    oracle = BehavioralOracle()
    res = await oracle.validate(project_id, Path("."), None)
    
    # Verify that the orphaned database schema triggers a failure
    assert not res.passed
    assert "schema_orphan" in res.reason


@pytest.mark.asyncio
async def test_runtime_oracle_execution():
    """Verify that RuntimeOracle executes pytest runs and returns operational output traces."""
    from app.sentinel.oracles.runtime_oracle import RuntimeOracle

    with tempfile.TemporaryDirectory() as tmp_dir:
        proj_path = Path(tmp_dir)
        project_id = "runtime_oracle_test"

        # Create dummy tests directory
        tests_dir = proj_path / "Backend" / "tests"
        tests_dir.mkdir(parents=True)
        
        # Write basic passing unit test
        with open(tests_dir / "test_dummy.py", "w", encoding="utf-8") as f:
            f.write("def test_ok():\n    assert True\n")

        oracle = RuntimeOracle()
        res = await oracle.validate(project_id, proj_path, None)
        
        assert res.passed
        assert res.evidence_key.startswith("ev-runtime-pass-")


@pytest.mark.asyncio
async def test_visual_and_semantic_soft_advisories():
    """Verify that VisualOracle and SemanticOracle report advisories but always pass cycle validation."""
    from app.sentinel.oracles.visual_oracle import VisualOracle
    from app.sentinel.oracles.semantic_oracle import SemanticOracle
    from app.models.directive import IntentField
    from app.sentinel.topology.topology_version_manager import TopologyVersionManager

    with tempfile.TemporaryDirectory() as tmp_dir:
        proj_path = Path(tmp_dir)
        project_id = "soft_oracles_test"

        # 1. Visual Oracle: Write dummy TSX file with Tailwind spacing warnings
        frontend_src = proj_path / "Frontend" / "src"
        frontend_src.mkdir(parents=True)
        with open(frontend_src / "Comp.tsx", "w", encoding="utf-8") as f:
            f.write("export default function Comp() {\n  return <div className='p-broken'>Item</div>;\n}")

        oracle_vis = VisualOracle()
        res_vis = await oracle_vis.validate(project_id, proj_path, None)
        
        # Soft validation always passes
        assert res_vis.passed
        assert res_vis.metrics["advisories_count"] > 0
        assert "p-broken" in res_vis.reason

        # 2. Semantic Oracle
        from app.sentinel.directives import IntentField as SentinelIntentField
        intent = IntentField(project_id=project_id, domain_entities=[DomainEntity(name="Project", description="...")])
        
        # Set IntentField Beanie get_pymongo_collection mock
        IntentField.get_pymongo_collection = MagicMock()
        SentinelIntentField.get_pymongo_collection = MagicMock()
        
        # Mock IntentField database retrieval
        from unittest.mock import AsyncMock
        IntentField.find_one = AsyncMock(return_value=intent)
        SentinelIntentField.find_one = AsyncMock(return_value=intent)


        # Mock ProjectTopologyGraph without Project entity (semantic drift!)
        graph = ProjectTopologyGraph(project_id=project_id)
        graph.update_graph_hash()
        TopologyVersionManager.get_active_topology = AsyncMock(return_value=graph)

        oracle_sem = SemanticOracle()
        res_sem = await oracle_sem.validate(project_id, proj_path, None)
        
        # Soft validation always passes
        assert res_sem.passed
        assert res_sem.metrics["drift_warnings_count"] > 0
        assert "Project" in res_sem.reason


@pytest.mark.asyncio
async def test_evidence_registry_grounding():
    """Verify that EvidenceRegistry persists validation traces as claim keys."""
    from app.governance.evidence_registry import EvidenceRegistry, EvidenceRecord

    # Mock EvidenceRecord Beanie collection getter
    EvidenceRecord.get_pymongo_collection = MagicMock()
    
    # Mock Beanie ODM methods for Beanie insert
    insert_mock = AsyncMock()
    EvidenceRecord.insert = insert_mock

    payload = {"status": "success", "assertions": 12}
    ev_key = await EvidenceRegistry.register_evidence("test_proj", "syntax_oracle", payload)
    
    assert ev_key.startswith("ev-ground-")
    assert insert_mock.called


@pytest.mark.asyncio
async def test_oracle_pipeline_integration():
    """Verify that OraclePipeline runs the multi-layer stack and stops on hard failures."""
    from app.sentinel.oracles.pipeline import OraclePipeline
    from app.governance.evidence_registry import EvidenceRegistry, EvidenceRecord

    # Mock DB methods for registry
    EvidenceRecord.get_pymongo_collection = MagicMock()
    EvidenceRecord.insert = AsyncMock()

    class MockContext:
        def __init__(self, pid, ppath):
            self.project_id = pid
            self.project_path = ppath
            self.files_written = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        proj_path = Path(tmp_dir)
        project_id = "pipeline_test"
        ctx = MockContext(project_id, proj_path)

        # Commit structurally flawed topology (empty graph triggers BehavioralOracle hard failure!)
        from app.sentinel.topology.topology_version_manager import TopologyVersionManager
        graph = ProjectTopologyGraph(project_id=project_id)
        graph.add_node("schema_orphan", NodeType.SCHEMA_NODE)
        graph.update_graph_hash()
        TopologyVersionManager.get_active_topology = AsyncMock(return_value=graph)

        # Write manifest file
        manifest_path = proj_path / ".genx_ast_manifest.json"
        manifest_data = {"project_id": project_id, "topology": graph.serialize()}
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f)

        # Mock IntentField and RuntimeTransaction queries to prevent Beanie initialization errors
        from app.models.directive import IntentField
        from app.models.runtime_models import RuntimeTransaction
        IntentField.find_one = AsyncMock(return_value=None)
        RuntimeTransaction.find = MagicMock(return_value=MagicMock(to_list=AsyncMock(return_value=[])))

        # Verify that running the pipeline halts on hard behavioral validation failure
        with pytest.raises(ValueError) as exc_info:
            await OraclePipeline.run(ctx)
        
        assert "HARD Oracle" in str(exc_info.value)
        assert "failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_runtime_projection_validator_parity():
    """Verify that RuntimeProjectionValidator monitors filesystem parity against AST projections."""
    from app.sentinel.runtime.runtime_projection_validator import RuntimeProjectionValidator
    from app.sentinel.topology.topology_version_manager import TopologyVersionManager
    from app.sentinel.runtime.drift_detection import DriftSeverity, DriftResponse

    with tempfile.TemporaryDirectory() as tmp_dir:
        proj_path = Path(tmp_dir)
        project_id = "sensory_cortex_test"

        # 1. Write dummy files
        file1 = proj_path / "file1.py"
        file1.write_text("print('hello')", encoding="utf-8")
        hash1 = hashlib.sha256(b"print('hello')").hexdigest()

        # 2. Write manifest matching file1.py
        manifest_path = proj_path / ".genx_ast_manifest.json"
        manifest_data = {
            "project_id": project_id,
            "topology": {"graph_hash": "graph_123"},
            "projections": {"file1.py": hash1}
        }
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f)

        # Mock DB active topology matching graph_hash
        graph = ProjectTopologyGraph(project_id=project_id)
        graph.graph_hash = "graph_123"
        TopologyVersionManager.get_active_topology = AsyncMock(return_value=graph)

        # Parity scan — should be clean
        report = await RuntimeProjectionValidator.validate_parity(project_id, proj_path)
        assert report.congruence_score == 1.0
        assert report.severity == DriftSeverity.CLEAN
        assert report.recommended_response == DriftResponse.NONE

        # 3. Create mismatch (modify file1.py)
        file1.write_text("print('hello modified')", encoding="utf-8")
        
        report_mismatch = await RuntimeProjectionValidator.validate_parity(project_id, proj_path)
        assert report_mismatch.congruence_score == 0.0
        assert "file1.py" in report_mismatch.mismatched_files
        assert report_mismatch.severity == DriftSeverity.SEVERE
        assert report_mismatch.recommended_response == DriftResponse.RECONSTRUCT


@pytest.mark.asyncio
async def test_reality_sync_synchronize():
    """Verify that RealitySync correctly computes cryptographic structural integrity chained hashes."""
    from app.sentinel.runtime.reality_sync import RealitySync
    from app.governance.evidence_registry import EvidenceRecord
    from app.models.runtime_models import RuntimeTransaction

    # Mock Beanie ODM methods
    EvidenceRecord.get_pymongo_collection = MagicMock()
    RuntimeTransaction.get_pymongo_collection = MagicMock()

    # Mock latest transaction history query returning prev committed transaction
    prev_tx = RuntimeTransaction(
        project_id="sync_hash_test",
        lease_id="lease_123",
        mutation_tier=MutationTier.TOPOLOGY,
        snapshot_id="snap_123",
        status=TransactionStatus.COMMITTED,
        tx_hash="prev_committed_hash_999"
    )
    
    # Mock Beanie ODM find query returning prev_tx with support for chained sort()
    find_mock = MagicMock()
    sort_mock = MagicMock()
    to_list_mock = AsyncMock(return_value=[prev_tx])
    RuntimeTransaction.find = find_mock
    find_mock.return_value = sort_mock
    sort_mock.sort.return_value = sort_mock
    sort_mock.to_list = to_list_mock

    with tempfile.TemporaryDirectory() as tmp_dir:
        proj_path = Path(tmp_dir)
        project_id = "sync_hash_test"

        # Write manifest file
        manifest_path = proj_path / ".genx_ast_manifest.json"
        manifest_data = {
            "project_id": project_id,
            "topology": {"graph_hash": "topo_graph_777"},
            "projections": {}
        }
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f)

        # Mock DB active topology graph
        graph = ProjectTopologyGraph(project_id=project_id)
        graph.graph_hash = "topo_graph_777"
        TopologyVersionManager.get_active_topology = AsyncMock(return_value=graph)

        # Run RealitySync and assert system chained integrity hashes
        sync_res = await RealitySync.synchronize_reality(project_id, proj_path)
        assert sync_res.is_synchronized
        assert sync_res.prev_tx_hash == "prev_committed_hash_999"
        assert len(sync_res.system_hash) == 64


@pytest.mark.asyncio
async def test_reality_sync_collapse_and_freeze():
    """Verify that RealitySync raises RealityDivergenceCollapse on severe mismatches without self-healing."""
    from app.sentinel.runtime.reality_sync import RealitySync, RealityDivergenceCollapse
    from app.models.runtime_models import ExecutionLease, RuntimeTransaction
    from app.models.workflow import WorkflowSession

    # Mock Beanie ODM collections
    ExecutionLease.get_pymongo_collection = MagicMock()
    RuntimeTransaction.get_pymongo_collection = MagicMock()
    WorkflowSession.get_pymongo_collection = MagicMock()

    # Mock lease revoking queries
    ExecutionLease.find = MagicMock(return_value=MagicMock(to_list=AsyncMock(return_value=[])))
    WorkflowSession.find_one = AsyncMock(return_value=None)

    with tempfile.TemporaryDirectory() as tmp_dir:
        proj_path = Path(tmp_dir)
        project_id = "collapse_test"

        # Run without a manifest file (triggers severe drift)
        with pytest.raises(RealityDivergenceCollapse) as exc_info:
            await RealitySync.synchronize_reality(project_id, proj_path)

        assert "congruence=0.0" in str(exc_info.value)
        assert "severity=severe" in str(exc_info.value)


@pytest.mark.asyncio
async def test_forensic_reconstruction():
    """Verify that ForensicReconstruction deterministically parses manifest evidence to recover canonical topology."""
    from app.sentinel.runtime.reconstruction import ForensicReconstruction
    from app.sentinel.topology.topology_version_manager import TopologyVersionRecord

    TopologyVersionRecord.get_pymongo_collection = MagicMock()
    TopologyVersionRecord.insert = AsyncMock()

    with tempfile.TemporaryDirectory() as tmp_dir:
        proj_path = Path(tmp_dir)
        project_id = "recon_test"

        # Add node to active graph template
        graph = ProjectTopologyGraph(project_id=project_id)
        graph.add_node("schema_project", NodeType.SCHEMA_NODE)
        graph.update_graph_hash()

        # Write manifest file
        manifest_path = proj_path / ".genx_ast_manifest.json"
        manifest_data = {
            "project_id": project_id,
            "topology": graph.serialize(),
            "projections": {}
        }
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f)

        # Clear active DB cache (mock returning None)
        TopologyVersionManager.get_active_topology = AsyncMock(side_effect=[None, graph])

        # Run forensic recovery
        recovered_graph = await ForensicReconstruction.reconstruct_topology(project_id, proj_path)
        assert recovered_graph.graph_hash == graph.graph_hash
        assert "schema_project" in recovered_graph.nodes


@pytest.mark.asyncio
async def test_ast_generator_deep_mappings():
    """Verify expanded ASTGenerator maps complex routes, optional schema fields, and react fetch hooks."""
    from app.sentinel.topology.ast_generator import ASTGenerator
    
    graph = ProjectTopologyGraph(project_id="deep_ast_test")
    
    # 1. Add schema node with optional fields
    graph.add_node("schema_task", NodeType.SCHEMA_NODE, {
        "entity_name": "Task",
        "fields": [
            {"name": "title", "type": "str", "required": True},
            {"name": "completed", "type": "bool", "required": False}
        ]
    })
    
    # 2. Add API node with endpoints and binds edge
    graph.add_node("api_tasks", NodeType.API_NODE, {
        "router_name": "tasks",
        "endpoints": [
            {"path": "/tasks", "method": "GET"},
            {"path": "/tasks", "method": "POST"},
            {"path": "/tasks/{id}", "method": "DELETE"}
        ]
    })
    graph.add_edge("api_tasks", "schema_task", "binds_schema")
    
    # 3. Add UI component with route bindings
    graph.add_node("ui_task_list", NodeType.UI_NODE, {
        "component_name": "TaskList",
        "features": ["sorting", "filtering"]
    })
    graph.add_node("route_tasks", NodeType.ROUTE_NODE, {"path": "/api/v1/tasks"})
    graph.add_edge("ui_task_list", "route_tasks", "binds_route")
    
    graph.update_graph_hash()
    
    ast_files = ASTGenerator.generate(graph)
    
    # Assert Beanie Optional Model Fields mapping
    model_file = ast_files["Backend/app/models/runtime_models.py"]
    todo_class = model_file.classes[0]
    assert todo_class.name == "Task"
    assert todo_class.fields[0].name == "title"
    assert todo_class.fields[0].type_str == "str"
    assert todo_class.fields[1].name == "completed"
    assert todo_class.fields[1].type_str == "Optional[bool]"
    
    # Assert active FastAPI Beanie CRUD generation
    router_file = ast_files["Backend/app/api/tasks.py"]
    routes = router_file.routes
    assert len(routes) == 3
    get_route = next(r for r in routes if r.method == "GET")
    post_route = next(r for r in routes if r.method == "POST")
    delete_route = next(r for r in routes if r.method == "DELETE")
    
    assert "await Task.find_all().to_list()" in get_route.body[0]
    assert "await payload.insert()" in post_route.body[0]
    assert "await item.delete()" in delete_route.body[3]
    
    # Assert React async fetch hook mapping
    ui_file = ast_files["Frontend/src/components/TaskList.tsx"]
    comp = ui_file.components[0]
    assert comp.name == "TaskList"
    assert "await fetch('/api/v1/tasks')" in comp.hooks[0]




