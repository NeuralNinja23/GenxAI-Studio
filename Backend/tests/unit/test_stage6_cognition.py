# tests/unit/test_stage6_cognition.py

"""

V4 Stage 6 Automated Verification Suite.

Asserts that minimal cognition, branch pruning, SQLite failure geometry,

NumPy-based repulsion, constraint physics, and non-authoritative faculties perform correctly.

"""



import os

import json

import sqlite3

import numpy as np

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

from app.sentinel.cognition.mutation_engine import MutationEngine

from app.sentinel.cognition.sentinel_core import SentinelCore

from app.sentinel.failure_memory.failure_geometry import FailureGeometry

from app.sentinel.failure_memory.repulsion_engine import RepulsionEngine

from app.agents.sub_agents import (

    VictoriaUIFaculty,

    DerekAPIFaculty,

    LunaSchemaFaculty,

    ReggieWorkflowFaculty,

    MarcusGovernanceAnalyst,

)



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

        schema_node_count=2

    )



    # Insert into database

    geom.insert_failure(

        failure_id="fail-1",

        vector=vec1,

        error_class="topology",

        cycle_id="cycle-123",

        details="Cyclic topology failure in dashboard views"

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





def test_repulsion_engine_deflection():

    db_path = "tests/unit/temp_repulsion_memory.db"

    if os.path.exists(db_path):

        os.remove(db_path)



    geom = FailureGeometry(db_path)

    engine = RepulsionEngine(geom)



    # Encode and insert an error vector

    err_vec = FailureGeometry.encode_failure(5, 5, False, "syntax", 2, 50, 1, 3, 1)

    geom.insert_failure("fail-sim", err_vec, "syntax", "c-1", "Syntax check failed")



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





@pytest.mark.asyncio

async def test_marcus_governance_analyst_scoring(base_graph):

    # Branch displays high repulsion score

    unstable_branch = BranchState(

        branch_id="unstable-b",

        topology_graph=base_graph,

        repulsion_score=0.7

    )



    mock_response = json.dumps({

        "governance_decision": "REJECT",

        "metrics": {

            "branch_entropy": 0.8,

            "topology_drift": 0.9,

            "repulsion_index": 0.7

        },

        "issues": [{"severity": "error", "description": "Severe repulsion index failure."}]

    })



    with patch("app.agents.sub_agents.call_llm", new_callable=AsyncMock) as mock_call, \
         patch("app.agents.sub_agents.SentinelVerificationGate.verify") as mock_verify:
        from app.sentinel.verification.verification_gate import VerificationResult
        mock_verify.return_value = VerificationResult()
        mock_call.return_value = mock_response

        mock_call.return_value = mock_response

        res = await MarcusGovernanceAnalyst.analyze_governance(unstable_branch)



    assert res["is_stable"] is False

    assert res["marcus_advisory_modifier"] < 1.0

    assert len(res["warnings"]) > 0



    # Non-authoritative assertion: Marcus emits dict values, does not mutate topology

    assert isinstance(res, dict)

    assert unstable_branch.topology_graph.nodes["dashboard_view"].integrity_hash != ""





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

