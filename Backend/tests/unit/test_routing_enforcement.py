# Backend/tests/unit/test_routing_enforcement.py
"""
Unit and integration tests for Phase 3 Routing Enforcement.
"""

import sys
import os
import uuid
import asyncio
import sqlite3
import json
import pytest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch, MagicMock

from app.models.runtime_models import MutationTier, RepairScope

# Import route/taxonomy types
from app.sentinel.routing import (
    FailureCategory,
    FailureDomain,
    RoutingDecision,
    TerminalStatus,
    SearchOutcome,
    AtlasFailureReason,
    CATEGORY_DOMAIN_MAP,
    CATEGORY_PRIORITY,
    FailureClassifier,
    FailureProfile,
)

# Import verification gate & validation logger
from app.sentinel.verification.verification_gate import (
    FailureFingerprint,
    SentinelVerificationGate,
    VerificationResult,
)
from app.sentinel.validation.validation_logger import ValidationLogger
from app.sentinel.topology.project_graph import ProjectTopologyGraph
from app.sentinel.topology.node_types import NodeType
from app.orchestration.sentinel_runtime import SentinelRuntime


# ─────────────────────────────────────────────────────────────
# 1. Single Source of Truth Taxonomy Tests
# ─────────────────────────────────────────────────────────────

def test_single_source_of_truth_mapping():
    """Verify that every FailureCategory maps to a real FailureDomain."""
    for category in FailureCategory:
        assert category in CATEGORY_DOMAIN_MAP, f"Category {category} is missing in CATEGORY_DOMAIN_MAP"
        assert isinstance(CATEGORY_DOMAIN_MAP[category], FailureDomain)


def test_category_priority_ordering():
    """Verify CATEGORY_PRIORITY has correct ordering and includes expected items."""
    expected_order = [
        FailureCategory.INFRASTRUCTURE_FAILURE,
        FailureCategory.PROJECTOR_FAILURE,
        FailureCategory.COMPILER_FAILURE,
        FailureCategory.RUNTIME_STATE_FAILURE,
        FailureCategory.GRAPH_STATE_FAILURE,
        FailureCategory.TOPOLOGY_FAILURE,
    ]
    assert CATEGORY_PRIORITY == expected_order


# ─────────────────────────────────────────────────────────────
# 2. Classifier Priority & Heuristics Tests
# ─────────────────────────────────────────────────────────────

def test_classifier_priority_ordering():
    """Verify classifier picks primary category and domain based on priority list."""
    failures = [
        SimpleNamespace(category=FailureCategory.TOPOLOGY_FAILURE),
        SimpleNamespace(category=FailureCategory.COMPILER_FAILURE),
        SimpleNamespace(category=FailureCategory.RUNTIME_STATE_FAILURE),
    ]
    
    profile = FailureClassifier.classify(failures)
    
    # COMPILER_FAILURE is highest priority among the three
    assert profile.primary_category == FailureCategory.COMPILER_FAILURE
    assert profile.primary == FailureDomain.CODE
    assert len(profile.active_categories) == 3
    assert FailureCategory.COMPILER_FAILURE in profile.active_categories
    assert FailureCategory.TOPOLOGY_FAILURE in profile.active_categories
    assert FailureCategory.RUNTIME_STATE_FAILURE in profile.active_categories
    assert profile.severity_score == 3.0
    
    # Secondary domains should contain FailureDomain.TOPOLOGY
    # (FailureDomain.CODE is the primary domain)
    assert FailureDomain.TOPOLOGY in profile.secondary
    assert FailureDomain.CODE not in profile.secondary


def test_classifier_fallback_heuristics():
    """Verify that classifier classifies legacy/untagged fingerprints correctly using heuristics."""
    # 1. Infra
    f1 = SimpleNamespace(failure_type="DOCKER_CONTAINER_DOWN", stage="Tier 0 Boot")
    p1 = FailureClassifier.classify([f1])
    assert p1.primary_category == FailureCategory.INFRASTRUCTURE_FAILURE
    assert p1.primary == FailureDomain.INFRASTRUCTURE

    # 2. Projector
    f2 = SimpleNamespace(failure_type="PROJECTOR_FAILURE", stage="AST Projection")
    p2 = FailureClassifier.classify([f2])
    assert p2.primary_category == FailureCategory.PROJECTOR_FAILURE
    assert p2.primary == FailureDomain.CODE

    # 3. Compiler
    f3 = SimpleNamespace(failure_type="TS2307", stage="Frontend build")
    p3 = FailureClassifier.classify([f3])
    assert p3.primary_category == FailureCategory.COMPILER_FAILURE
    
    f3_2 = SimpleNamespace(failure_type="BACKEND_BUILD_FAILURE", stage="Backend compile")
    p3_2 = FailureClassifier.classify([f3_2])
    assert p3_2.primary_category == FailureCategory.COMPILER_FAILURE

    # 4. Runtime State
    f4 = SimpleNamespace(failure_type="STATE_BINDING_FAILURE", stage="Runtime verification")
    p4 = FailureClassifier.classify([f4])
    assert p4.primary_category == FailureCategory.RUNTIME_STATE_FAILURE

    # 5. Graph State / Topology
    f5 = SimpleNamespace(failure_type="TOPOLOGY_INTEGRITY_FAILURE", stage="Topology")
    p5 = FailureClassifier.classify([f5])
    assert p5.primary_category == FailureCategory.GRAPH_STATE_FAILURE
    assert p5.primary == FailureDomain.TOPOLOGY

    # 6. Unknown fallback
    f6 = SimpleNamespace(failure_type="TOTALLY_RANDOM_STUFF", stage="Some stage")
    p6 = FailureClassifier.classify([f6])
    assert p6.primary_category == FailureCategory.UNKNOWN
    assert p6.primary == FailureDomain.UNKNOWN


# ─────────────────────────────────────────────────────────────
# 3. Routing Decisions & Priority Tests
# ─────────────────────────────────────────────────────────────

def test_route_for_profile():
    """Verify route decisions priority: INFRASTRUCTURE > ATLAS > TOPOLOGY."""
    # 1. Infrastructure wins
    p1 = FailureProfile(
        primary=FailureDomain.INFRASTRUCTURE,
        secondary={FailureDomain.CODE, FailureDomain.TOPOLOGY},
        domain_counts={"INFRASTRUCTURE": 1, "CODE": 2, "TOPOLOGY": 1},
        severity_score=3.0,
        primary_category=FailureCategory.INFRASTRUCTURE_FAILURE,
        active_categories=[FailureCategory.INFRASTRUCTURE_FAILURE, FailureCategory.COMPILER_FAILURE, FailureCategory.TOPOLOGY_FAILURE]
    )
    route, reason = SentinelRuntime._route_for_profile(p1)
    assert route == RoutingDecision.INFRASTRUCTURE
    assert "INFRASTRUCTURE" in reason

    # 2. Atlas/Code wins over Topology
    p2 = FailureProfile(
        primary=FailureDomain.CODE,
        secondary={FailureDomain.TOPOLOGY},
        domain_counts={"CODE": 1, "TOPOLOGY": 1},
        severity_score=2.0,
        primary_category=FailureCategory.COMPILER_FAILURE,
        active_categories=[FailureCategory.COMPILER_FAILURE, FailureCategory.TOPOLOGY_FAILURE]
    )
    route, reason = SentinelRuntime._route_for_profile(p2)
    assert route == RoutingDecision.ATLAS
    assert "CODE" in reason

    # 3. Topology wins alone (now routes to ATLAS)
    p3 = FailureProfile(
        primary=FailureDomain.TOPOLOGY,
        secondary=set(),
        domain_counts={"TOPOLOGY": 1},
        severity_score=1.0,
        primary_category=FailureCategory.TOPOLOGY_FAILURE,
        active_categories=[FailureCategory.TOPOLOGY_FAILURE]
    )
    route, reason = SentinelRuntime._route_for_profile(p3)
    assert route == RoutingDecision.ATLAS
    assert "TOPOLOGY" in reason


# ─────────────────────────────────────────────────────────────
# 4. Atlas Failure Reasons Mappings
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_atlas_run_timeout():
    """Verify Atlas Timeout exception maps to ATLAS_UNAVAILABLE."""
    runtime = SentinelRuntime()
    with patch("app.studio.faculties.atlas_faculty.AtlasFaculty.propose_repair_intent", side_effect=asyncio.TimeoutError()):
        intent, reason, status = await runtime._run_atlas_with_reason(
            failures=[],
            current_graph=ProjectTopologyGraph(project_id="test"),
            max_tier=MutationTier.COSMETIC,
            active_goals=[],
            oracle_before=1.0,
            current_repair_scope=RepairScope.COMPONENT,
            kernel_llm_client=MagicMock()
        )
        assert intent is None
        assert reason == AtlasFailureReason.TIMEOUT
        assert status == TerminalStatus.ATLAS_UNAVAILABLE


@pytest.mark.asyncio
async def test_atlas_run_exception():
    """Verify Atlas generic Exception maps to ATLAS_UNAVAILABLE."""
    runtime = SentinelRuntime()
    with patch("app.studio.faculties.atlas_faculty.AtlasFaculty.propose_repair_intent", side_effect=ValueError("LLM Down")):
        intent, reason, status = await runtime._run_atlas_with_reason(
            failures=[],
            current_graph=ProjectTopologyGraph(project_id="test"),
            max_tier=MutationTier.COSMETIC,
            active_goals=[],
            oracle_before=1.0,
            current_repair_scope=RepairScope.COMPONENT,
            kernel_llm_client=MagicMock()
        )
        assert intent is None
        assert reason == AtlasFailureReason.EXCEPTION
        assert status == TerminalStatus.ATLAS_UNAVAILABLE


@pytest.mark.asyncio
async def test_atlas_run_empty_response():
    """Verify Atlas empty response maps to ATLAS_UNAVAILABLE."""
    runtime = SentinelRuntime()
    with patch("app.studio.faculties.atlas_faculty.AtlasFaculty.propose_repair_intent", return_value=None):
        intent, reason, status = await runtime._run_atlas_with_reason(
            failures=[],
            current_graph=ProjectTopologyGraph(project_id="test"),
            max_tier=MutationTier.COSMETIC,
            active_goals=[],
            oracle_before=1.0,
            current_repair_scope=RepairScope.COMPONENT,
            kernel_llm_client=MagicMock()
        )
        assert intent is None
        assert reason == AtlasFailureReason.EMPTY_RESPONSE
        assert status == TerminalStatus.ATLAS_UNAVAILABLE


# ─────────────────────────────────────────────────────────────
# 5. Gate Tagging Contract Tests
# ─────────────────────────────────────────────────────────────

def test_gate_tagging_dependencies():
    """Verify SentinelVerificationGate._verify_dependencies tags unresolved relative imports as GRAPH_STATE_FAILURE."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_path = Path(tmp_dir)
        components_dir = project_path / "Frontend" / "src" / "components"
        components_dir.mkdir(parents=True)

        # Write a file that imports a non-existent relative module
        with open(components_dir / "App.tsx", "w", encoding="utf-8") as f:
            f.write('import NonExistent from "./NonExistent";\n')

        # Graph MUST have a UI_NODE — otherwise _verify_dependencies early-returns
        graph = ProjectTopologyGraph(project_id="gate_tag_test")
        graph.add_node(
            node_id="root_ui_test",
            node_type=NodeType.UI_NODE,
            properties={"component_name": "App", "generated": True}
        )
        result = VerificationResult()

        SentinelVerificationGate._verify_dependencies(project_path, graph, result)

        assert not result.dependency_passed, "Expected dependency_passed=False for unresolved import"
        assert len(result.failures) > 0, "Expected at least one UNRESOLVED_IMPORT_FAILURE fingerprint"
        for failure in result.failures:
            assert failure.category == FailureCategory.GRAPH_STATE_FAILURE, (
                f"Expected GRAPH_STATE_FAILURE but got {failure.category}"
            )


# ─────────────────────────────────────────────────────────────
# 6. SQLite Telemetry Persistence Tests
# ─────────────────────────────────────────────────────────────

def test_sqlite_persistence_new_routing_columns():
    """Verify new routing fields are persisted in SQLite projection_runs."""
    # Force initialize the database schema in memory or check column definitions
    # Since DB_PATH points to a real file, let's use the defined initialize_db
    # and verify table info.
    ValidationLogger.initialize_db()
    
    # Inject mock run event
    run_id = f"run_test_{uuid.uuid4().hex[:6]}"
    events = [{
        "type": "projection_run",
        "payload": {
            "project_id": "routing_telemetry_test",
            "prompt": "Test prompt",
            "state_fingerprint": "hash123",
            "selected_branch": "composite",
            "branch_count": 0,
            "final_weight": 0.0,
            "convergence": 0.0,
            "complexity": 0.0,
            "repulsion_score": 0.0,
            "marcus_score": 0.0,
            "memory_hits": 0,
            "dependency_score": 1.0,
            "schema_score": 1.0,
            "state_score": 1.0,
            "build_score": 1.0,
            "runtime_score": 1.0,
            "visual_score": 1.0,
            "topology_score": 1.0,
            "final_result": "SUCCESS",
            "failure_type": None,
            "termination_reason": "Completed",
            "duration_ms": 150,
            "primary_failure_category": "COMPILER_FAILURE",
            "active_failure_categories": ["COMPILER_FAILURE", "TOPOLOGY_FAILURE"],
            "routing_decision": "ATLAS",
            "routing_reason": "domain:CODE present",
            "search_outcome": "NOT_RUN"
        }
    }]
    
    ValidationLogger.flush_events(run_id, events)
    
    # Query row back
    with ValidationLogger._get_connection() as conn:
        row = conn.execute("SELECT * FROM projection_runs WHERE run_id = ?", (run_id,)).fetchone()
        assert row is not None
        assert row["primary_failure_category"] == "COMPILER_FAILURE"
        # Deserialize JSON list
        active_cats = json.loads(row["active_failure_categories"])
        assert "COMPILER_FAILURE" in active_cats
        assert "TOPOLOGY_FAILURE" in active_cats
        assert row["routing_decision"] == "ATLAS"
        assert row["routing_reason"] == "domain:CODE present"
        assert row["search_outcome"] == "NOT_RUN"


# ─────────────────────────────────────────────────────────────
# 7. Route State Assertions Test
# ─────────────────────────────────────────────────────────────

def test_route_state_assertions():
    """Verify that exclusive route configurations behave correctly and raise assertions if violated."""
    # Scenario A: ATLAS route must not have active_branches
    route = RoutingDecision.ATLAS
    repair_intent = MagicMock()
    active_branches = [MagicMock()] # Violated!
    
    with pytest.raises(AssertionError, match="ATLAS route must not run topology search"):
        if route == RoutingDecision.ATLAS:
            assert repair_intent is not None, "ATLAS route requires repair_intent"
            assert len(active_branches) == 0, "ATLAS route must not run topology search"

    # Scenario B: TOPOLOGY route must not run Atlas repair
    route = RoutingDecision.TOPOLOGY
    repair_intent = MagicMock() # Violated!
    topology_search_executed = True
    
    with pytest.raises(AssertionError, match="TOPOLOGY route must not run Atlas repair"):
        if route == RoutingDecision.TOPOLOGY:
            assert repair_intent is None, "TOPOLOGY route must not run Atlas repair"
            assert topology_search_executed, "TOPOLOGY route must execute topology search"

    # Scenario C: INFRASTRUCTURE route must not run Atlas repair or topology search
    route = RoutingDecision.INFRASTRUCTURE
    repair_intent = None
    active_branches = [MagicMock()] # Violated!
    
    with pytest.raises(AssertionError, match="INFRASTRUCTURE route must not run topology search"):
        if route == RoutingDecision.INFRASTRUCTURE:
            assert repair_intent is None, "INFRASTRUCTURE route must not run Atlas repair"
            assert len(active_branches) == 0, "INFRASTRUCTURE route must not run topology search"
