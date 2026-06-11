# tests/unit/test_stage6_cognition.py

"""

V4 Stage 6 Automated Verification Suite.

Asserts that minimal cognition, branch pruning, SQLite failure geometry,

NumPy-based repulsion, constraint physics, and non-authoritative faculties perform correctly.

"""



import os

import json

import sqlite3
import shutil

import tempfile

import numpy as np

from pathlib import Path

import pytest

from app.models.directive import IntentField, SemanticConstraint

from app.models.runtime_models import MutationTier

from app.sentinel.topology.project_graph import ProjectTopologyGraph

from app.sentinel.topology.node_types import NodeType

from unittest.mock import MagicMock, AsyncMock, patch

from app.sentinel.cognition.patch_ir import PatchIR

from app.sentinel.cognition.branch import BranchState, BranchTreeManager

from app.sentinel.cognition.constraint_engine import ConstraintEngine

from app.sentinel.cognition.convergence_engine import ConvergenceEngine

from app.sentinel.cognition.attention_router import AttentionRouter

from app.studio.mutation.mutation_engine import MutationEngine

from app.sentinel.cognition.sentinel_core import SentinelCore

from app.sentinel.failure_memory.failure_geometry import FailureGeometry

from app.sentinel.failure_memory.repulsion_engine import RepulsionEngine
from app.sentinel.topology.ast_projector import ASTProjector

from app.studio.faculties.victoria import VictoriaUIFaculty
from app.studio.faculties.derek import DerekAPIFaculty
from app.studio.faculties.luna import LunaSchemaFaculty
from app.studio.faculties.reggie import ReggieWorkflowFaculty



@pytest.fixture(scope="session", autouse=True)

def init_beanie_mock():

    """Mock Beanie ODM collection getter so documents can be instantiated without direct DB connection."""

    IntentField.get_pymongo_collection = MagicMock()





@pytest.fixture

def base_graph():

    graph = ProjectTopologyGraph(project_id="test-proj")

    graph.add_node(

        node_id="dashboard_view",

        node_type=NodeType.UI_NODE,

        properties={"component_name": "Dashboard", "is_root": True}

    )

    return graph





@pytest.fixture

def intent_field():

    return IntentField(

        project_id="test-proj",

        invariants=["Auth boundaries must be preserved."],

        constraints=[

            SemanticConstraint(

                rule_id="db-constraint",

                description="Database logic requires topology tier",

                severity="HARD",

                validation_target="DB"

            )

        ]

    )





def test_constraint_engine_tier5_block(intent_field):

    # Propose Tier 5 Forbidden Mutation

    forbidden_patch = PatchIR(

        target_node_id="execution_kernel",

        mutation_tier=MutationTier.FORBIDDEN,

        action="UPDATE_NODE",

        node_data={"properties": {"override_safety": True}}

    )



    res = ConstraintEngine.validate_mutation(forbidden_patch, intent_field)

    assert res.passed is False

    assert any("Forbidden" in v or "Kernel" in v for v in res.violations)





def test_constraint_engine_invariant_block(intent_field):

    # Attempt to delete security boundary node

    unsafe_patch = PatchIR(

        target_node_id="user_auth_service",

        mutation_tier=MutationTier.TOPOLOGY,

        action="REMOVE_NODE"

    )



    res = ConstraintEngine.validate_mutation(unsafe_patch, intent_field)

    assert res.passed is False

    assert any("invariant" in v.lower() for v in res.violations)





def test_branch_cloning_and_tree_spawning(base_graph):

    tree = BranchTreeManager()

    root = BranchState(topology_graph=base_graph)

    tree.active_branches[root.branch_id] = root



    # Propose valid patch

    patch = PatchIR(

        target_node_id="analytics_panel",

        mutation_tier=MutationTier.STRUCTURAL_UI,

        action="ADD_NODE",

        node_data={"node_type": "UI_NODE", "properties": {"component_name": "AnalyticsPanel"}}

    )



    child = tree.spawn_branch(root, patch)

    assert child.parent_branch_id == root.branch_id

    assert "analytics_panel" in child.topology_graph.nodes

    assert child.topology_graph.nodes["analytics_panel"].node_type == NodeType.UI_NODE





def test_failure_geometry_encoding_and_sqlite():

    # Setup temporary local SQLite database for failure memory

    db_path = "tests/unit/temp_failure_memory.db"

    if os.path.exists(db_path):

        os.remove(db_path)

    geom = FailureGeometry(db_path)

    # Encode a specific failure
    vec1 = FailureGeometry.encode_failure(
        node_count=10,
        edge_count=15,
        is_cyclic=True,
        error_class="topology",
        mutation_tier=4,
        error_len=200,
        api_node_count=3,
        ui_node_count=4,
        schema_node_count=2,
    )

    # Insert into database
    geom.insert_failure(
        failure_id="fail-1",
        vector=vec1,
        error_class="topology",
        cycle_id="cycle-123",
        details="Cyclic topology failure in dashboard views",
    )

    # Fetch from database
    failures = geom.get_all_failures()
    assert len(failures) == 1
    f_id, vec_retrieved, err_class, cyc_id, details = failures[0]
    assert f_id == "fail-1"
    assert err_class == "topology"
    assert cyc_id == "cycle-123"
    assert np.allclose(vec1, vec_retrieved)

    # Clean up
    if os.path.exists(db_path):
        os.remove(db_path)



def test_failure_geometry_records_verification_stage():

    db_path = "tests/unit/temp_failure_memory_stage.db"

    if os.path.exists(db_path):

        os.remove(db_path)

    geom = FailureGeometry(db_path)

    vec = FailureGeometry.encode_failure(
        node_count=12,
        error_class="WIRING_FAILURE",
        mutation_tier=4,
        error_len=80,
        ui_node_count=5,
    )

    geom.insert_failure(
        failure_id="fail-stage-1",
        vector=vec,
        error_class="WIRING_FAILURE",
        cycle_id="cycle-stage",
        details="Frontend route wiring aborted",
        verification_stage="Dynamic Route Wiring",
    )

    rows = geom.mal.load_all_records()
    assert len(rows) == 1

    f_id, _, err_class, cyc_id, details, stage, *_ = rows[0]
    assert f_id == "fail-stage-1"
    assert err_class == "WIRING_FAILURE"
    assert cyc_id == "cycle-stage"
    assert details == "Frontend route wiring aborted"
    assert stage == "Dynamic Route Wiring"



def test_ast_projector_atomic_promote_replaces_live_tree():

    with tempfile.TemporaryDirectory() as tmp_dir:

        root = Path(tmp_dir)
        project_path = root / "project"
        staging_path = root / ".staging"

        (project_path / "Frontend").mkdir(parents=True)
        (project_path / "Frontend" / "live.txt").write_text("live", encoding="utf-8")
        (staging_path / "Frontend").mkdir(parents=True)
        (staging_path / "Frontend" / "staged.txt").write_text("staged", encoding="utf-8")

        ASTProjector._atomic_promote_staging(project_path, staging_path)

        assert (project_path / "Frontend" / "staged.txt").read_text(encoding="utf-8") == "staged"
        assert not (project_path / "Frontend" / "live.txt").exists()
        assert not staging_path.exists()
        assert not (root / ".project.rollback_backup").exists()



def test_ast_projector_atomic_promote_rolls_back_on_failure(monkeypatch):

    with tempfile.TemporaryDirectory() as tmp_dir:

        root = Path(tmp_dir)
        project_path = root / "project"
        staging_path = root / ".staging"

        (project_path / "Frontend").mkdir(parents=True)
        (project_path / "Frontend" / "live.txt").write_text("live", encoding="utf-8")
        (staging_path / "Frontend").mkdir(parents=True)
        (staging_path / "Frontend" / "staged.txt").write_text("staged", encoding="utf-8")

        original_move = shutil.move

        def fail_on_stage_move(src, dst, *args, **kwargs):
            if Path(src).name == ".staging":
                raise RuntimeError("simulated promotion failure")
            return original_move(src, dst, *args, **kwargs)

        monkeypatch.setattr(shutil, "move", fail_on_stage_move)

        with pytest.raises(RuntimeError):
            ASTProjector._atomic_promote_staging(project_path, staging_path)

        assert (project_path / "Frontend" / "live.txt").read_text(encoding="utf-8") == "live"
        assert not (project_path / "Frontend" / "staged.txt").exists()





def test_repulsion_engine_deflection():

    db_path = "tests/unit/temp_repulsion_memory.db"

    if os.path.exists(db_path):

        os.remove(db_path)



    geom = FailureGeometry(db_path)

    engine = RepulsionEngine(geom)



    # Encode and insert an error vector

    err_vec = FailureGeometry.encode_failure(5, 5, False, "syntax", 2, 50, 1, 3, 1)

    geom.insert_failure("fail-sim", err_vec, "syntax", "c-1", "Syntax check failed", status="COMMITTED")



    # Encode a candidate vector that is identical (perfect similarity = 1.0)

    candidate_vec = FailureGeometry.encode_failure(5, 5, False, "syntax", 2, 50, 1, 3, 1)



    score = engine.get_repulsion_score(candidate_vec)

    assert np.isclose(score, 1.0)

    assert engine.check_repulsion_breach(candidate_vec, threshold=0.85) is True



    # Encode an entirely different vector (should have lower similarity)

    diff_vec = FailureGeometry.encode_failure(50, 80, True, "behavioral", 4, 300, 20, 10, 15)

    diff_score = engine.get_repulsion_score(diff_vec)

    assert diff_score < 0.85

    assert engine.check_repulsion_breach(diff_vec, threshold=0.85) is False



    # Clean up

    if os.path.exists(db_path):

        os.remove(db_path)





def test_convergence_engine_entropy():

    graph = ProjectTopologyGraph(project_id="test")

    # Entropy of an empty or singular graph

    entropy_0 = ConvergenceEngine.calculate_entropy(graph)

    assert entropy_0 == 0.0



    # Add different types of nodes to build entropy

    graph.add_node("n1", NodeType.UI_NODE)

    graph.add_node("n2", NodeType.API_NODE)

    graph.add_node("n3", NodeType.SCHEMA_NODE)



    entropy_1 = ConvergenceEngine.calculate_entropy(graph)

    assert entropy_1 > 0.0



    # Slope checks

    history = [1.5, 1.2, 1.0, 1.0, 1.0]

    assert ConvergenceEngine.calculate_slope(history) == 0.0

    assert ConvergenceEngine.is_stagnant(history) is True

    assert ConvergenceEngine.is_converged(history) is True





def test_attention_router_budget_pruning(base_graph):

    router = AttentionRouter(max_branches=3)



    branches = []

    for i in range(6):

        # Create different branches with incremental repulsion to scale their scores

        b = BranchState(

            branch_id=f"b-{i}",

            topology_graph=base_graph,

            repulsion_score=float(i / 10.0) # b-0 has 0.0 repulsion (best), b-5 has 0.5 (worst)

        )

        # Add basic entropy history to simulate slope

        b.entropy_history = [1.5, 1.5]

        branches.append(b)



    kept, pruned = router.prune_to_budget(branches)



    # Budget check

    assert len(kept) == 3

    assert len(pruned) == 3

    # Top ranked should be b-0 (highest attention weight)

    assert kept[0].branch_id == "b-0"

    assert pruned[0].is_pruned is True






def test_sentinel_core_exploration_pipeline(base_graph, intent_field):

    core = SentinelCore(max_branches=3)

    core.initialize_root(base_graph)



    # Propose three valid patches and one Tier 5 forbidden patch

    proposals = [

        PatchIR(

            target_node_id="analytics_panel",

            mutation_tier=MutationTier.STRUCTURAL_UI,

            action="ADD_NODE",

            node_data={"node_type": "UI_NODE"}

        ),

        PatchIR(

            target_node_id="get_analytics_endpoint",

            mutation_tier=MutationTier.BEHAVIORAL,

            action="ADD_NODE",

            node_data={"node_type": "API_NODE"}

        ),

        # Forbidden Tier 5 Mutation

        PatchIR(

            target_node_id="execution_kernel",

            mutation_tier=MutationTier.FORBIDDEN,

            action="UPDATE_NODE"

        )

    ]



    active = core.explore_possibilities(intent_field, proposals)



    # Forbidden patch should have been discarded (never created branch)

    # Remaining 2 patches spawned branches and composite branch, plus root

    assert len(active) == 4  # root + 2 new children + composite

    active_ids = [b.branch_id for b in active]

    assert "root" in active_ids





def test_mutation_engine_escape_proposals(base_graph):

    failed_branch = BranchState(topology_graph=base_graph)

    

    # Trigger escape under syntax oracle blockage

    feedback = {

        "failed_oracles": [{"name": "syntax_oracle", "message": "Syntax error in dashboard_view component compilation"}]

    }



    escapes = MutationEngine.propose_escape_mutations(failed_branch, "ORACLE_BLOCK", feedback)

    assert len(escapes) > 0

    assert escapes[0].target_node_id == "dashboard_view"

    assert escapes[0].mutation_tier == MutationTier.COSMETIC

    assert escapes[0].action == "UPDATE_NODE"


def test_linear_delta_alpha_drift_modifier(base_graph):
    # Tests that raw_score is adjusted by delta_alpha_modifier
    router = AttentionRouter(max_branches=3)
    branch = BranchState(
        branch_id="test_da",
        topology_graph=base_graph,
        attention_weight=1.0,
        previous_attention_weight=1.0
    )
    # Mock SentinelTopologyVerifier.verify to return no failures
    with patch("app.sentinel.verification.verification_gate.SentinelTopologyVerifier.verify") as mock_verify:
        from app.sentinel.verification.verification_gate import TopologyVerificationResult
        res = TopologyVerificationResult()
        res.dependency_graph_survival = 1.0
        res.schema_survival = 1.0
        res.route_survival = 1.0
        res.state_survival = 1.0
        res.topology_survival = 1.0
        res.failures = []
        mock_verify.return_value = res

        # Scored with previous weight = 1.0. Let's calculate the expected weight
        # raw_score should be 1.0 (all survival metrics are 1.0, repulsion and novelty also close to 1.0)
        # alpha_prev = 1.0
        # delta_alpha = raw_score - alpha_prev = 0.0
        # delta_alpha_modifier = 1.0 + (0.0 * 0.2) = 1.0
        # final_weight = raw_score * 1.0 * marcus_mod(1.0) * goal_completion(1.0) = 1.0
        # If we change previous_attention_weight to 0.5:
        # delta_alpha = 1.0 - 0.5 = 0.5
        # delta_alpha_modifier = 1.0 + (0.5 * 0.2) = 1.1
        # final_weight should be 1.0 * 1.1 = 1.1
        
        branch.attention_weight = 1.0
        branch.previous_attention_weight = 1.0
        w1 = router.calculate_branch_weight(branch)
        
        branch.attention_weight = 1.0
        branch.previous_attention_weight = 0.5
        # Reset the repulsion check flag so it runs again
        if hasattr(branch, "_repulsion_checked"):
            delattr(branch, "_repulsion_checked")
        w2 = router.calculate_branch_weight(branch)
        
        assert w2 > w1  # linear delta_alpha boost was applied


def test_conditional_hard_repulsion_gate(base_graph):
    # Setup temporary local SQLite database for failure memory
    db_path = "tests/unit/temp_repulsion_gate_test.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    try:
        geom = FailureGeometry(db_path)
        
        # 1. Store a historical state failure with 5 failures
        # Matches base_graph layout: 1 UI node, 0 edges, 0 api, 0 schema
        hist_vec = FailureGeometry.encode_failure(
            node_count=1,
            edge_count=0,
            is_cyclic=False,
            error_class="FRONTEND_BUILD_FAILURE",
            mutation_tier=2,
            error_len=25,
            api_node_count=0,
            ui_node_count=1,
            schema_node_count=0,
        )
        geom.mal.insert_failure_record(
            failure_id="hist-fail",
            vector=hist_vec,
            error_class="FRONTEND_BUILD_FAILURE",
            cycle_id="cycle-1",
            details="Frontend build failures details",
            verification_stage="E2E State Profile",
            status="COMMITTED",
            failure_count=5
        )

        # Mock FailureGeometry to use this db_path
        with patch("app.sentinel.failure_memory.failure_geometry.FailureGeometry.__init__", lambda self, *args, **kwargs: setattr(self, "mal", geom.mal)),              patch("app.sentinel.verification.verification_gate.SentinelTopologyVerifier.verify") as mock_verify:
            
            # Scenario A: Non-improving state (current failures = 5 >= historical failures = 5)
            # This should be PRUNED
            from app.sentinel.verification.verification_gate import TopologyVerificationResult, FailureFingerprint
            res_non_improving = TopologyVerificationResult()
            res_non_improving.dependency_graph_survival = 0.5
            res_non_improving.schema_survival = 0.5
            res_non_improving.route_survival = 0.5
            res_non_improving.state_survival = 0.5
            res_non_improving.topology_survival = 0.5
            # We create 5 failures to match historical count
            res_non_improving.failures = [
                FailureFingerprint(failure_type="FRONTEND_BUILD_FAILURE", details="err1", stage="stage1")
                for _ in range(5)
            ]
            mock_verify.return_value = res_non_improving

            router = AttentionRouter(max_branches=3)
            branch_a = BranchState(
                branch_id="branch_a",
                topology_graph=base_graph
            )
            
            # Mock log to capture repulsion gate logging
            with patch("app.core.logging.log") as mock_log:
                router.calculate_branch_weight(branch_a)
                
                # Verify that it was pruned
                assert branch_a.is_pruned is True
                
                # Check that [REPULSION_GATE] log was emitted with decision=PRUNE
                log_calls = [call[0][1] for call in mock_log.call_args_list if call[0][0] == "COGNITION"]
                assert any("[REPULSION_GATE]" in s and "decision=PRUNE" in s for s in log_calls)

            # Scenario B: Improving state (current failures = 2 < historical failures = 5)
            # This should be ALLOWED
            res_improving = TopologyVerificationResult()
            res_improving.dependency_graph_survival = 0.8
            res_improving.schema_survival = 0.8
            res_improving.route_survival = 0.8
            res_improving.state_survival = 0.8
            res_improving.topology_survival = 0.8
            # 2 failures
            res_improving.failures = [
                FailureFingerprint(failure_type="FRONTEND_BUILD_FAILURE", details="err1", stage="stage1")
                for _ in range(2)
            ]
            mock_verify.return_value = res_improving

            branch_b = BranchState(
                branch_id="branch_b",
                topology_graph=base_graph
            )
            
            with patch("app.core.logging.log") as mock_log:
                router.calculate_branch_weight(branch_b)
                
                # Verify that it is NOT pruned
                assert branch_b.is_pruned is False
                
                # Check that [REPULSION_GATE] log was emitted with decision=ALLOW
                log_calls = [call[0][1] for call in mock_log.call_args_list if call[0][0] == "COGNITION"]
                assert any("[REPULSION_GATE]" in s and "decision=ALLOW" in s for s in log_calls)

    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
