# app/oracles/semantic_oracle.py
"""
V4 Semantic Oracle — Stage 4: Oracle Layer

SOFT Oracle serving as an advisory-only semantic intent drift detector.
"""

from pathlib import Path
from typing import Any
import uuid

from app.core.logging import log
from app.sentinel.oracles.base import BaseOracle, OracleResult
from app.sentinel.directives import IntentField
from app.sentinel.topology.topology_version_manager import TopologyVersionManager

class SemanticOracle(BaseOracle):
    """
    Semantic Intent Alignment Oracle (SOFT).
    Measures how closely the active topology adheres to IntentField constraints.
    Advisory-only — never blocks hard validation or commits transactions.
    """

    def __init__(self):
        super().__init__(name="semantic_oracle", is_hard=False)

    async def validate(self, project_id: str, project_path: Path, cycle_ctx: Any) -> OracleResult:
        log("ORACLE", f"🔍 Running Semantic Oracle alignment assertions on {project_id}")

        from app.sentinel.topology.node_types import NodeType # import here to prevent circular references

        intent = await IntentField.find_one({"project_id": project_id})
        graph = await TopologyVersionManager.get_active_topology(project_id)

        if not intent or not graph:
            return OracleResult(
                passed=True,
                reason="Advisory: intent field or active topology graph missing. Cannot calculate drift.",
                evidence_key=f"ev-semantic-nodata-{str(uuid.uuid4())[:8]}"
            )

        drift_warnings = []
        
        # 1. Assert that all domain entities defined in IntentField are represented in the graph nodes
        for entity in intent.domain_entities:
            expected_node_id = f"schema_{entity.name.lower()}"
            if expected_node_id not in graph.nodes:
                drift_warnings.append(f"Domain entity '{entity.name}' defined in IntentField is missing in active topology.")

        # 2. Check for unexpected nodes not defined in intent (structural exploration space)
        # This is a key soft metric showing mutation explore rate!
        unmapped_nodes = 0
        for node_id, node in graph.nodes.items():
            if node.node_type == NodeType.SCHEMA_NODE and not any(entity.name.lower() in node_id for entity in intent.domain_entities):
                unmapped_nodes += 1

        passed = len(drift_warnings) == 0
        reason = "Active topology successfully aligned with all IntentField invariants." if passed else f"Intent alignment warnings: {drift_warnings}"
        evidence_key = f"ev-semantic-pass-{str(uuid.uuid4())[:8]}" if passed else f"ev-semantic-drift-{str(uuid.uuid4())[:8]}"

        return OracleResult(
            passed=True,  # SOFT Oracle always passes cycle validation
            reason=reason,
            metrics={"drift_warnings_count": len(drift_warnings), "unmapped_explore_nodes": unmapped_nodes},
            evidence_key=evidence_key
        )
