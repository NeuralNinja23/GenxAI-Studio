# app/oracles/behavioral_oracle.py
"""
V4 Behavioral Oracle — Stage 4: Oracle Layer

HARD Oracle enforcing workflow coherence, routing bindings, and contract connectivity.
"""

from pathlib import Path
from typing import Any
import uuid

from app.core.logging import log
from app.sentinel.oracles.base import BaseOracle, OracleResult
from app.sentinel.topology.node_types import NodeType
from app.sentinel.topology.topology_version_manager import TopologyVersionManager
from app.sentinel.failure_memory.failure_recorder import record_failure, FailureType, Severity

class BehavioralOracle(BaseOracle):
    """
    Workflow Coherence Oracle (HARD).
    Asserts that user actions, state bindings, API router paths, and DB models
    form connected end-to-end trace flows. No semantic reasoning.
    """

    def __init__(self):
        super().__init__(name="behavioral_oracle", is_hard=True)

    async def validate(self, project_id: str, project_path: Path, cycle_ctx: Any) -> OracleResult:
        log("ORACLE", f"🔍 Running Behavioral Oracle workflow validation on {project_id}")

        graph = await TopologyVersionManager.get_active_topology(project_id)
        if not graph:
            return OracleResult(
                passed=False,
                reason="Behavioral verification failed: active topology graph missing.",
                evidence_key=f"ev-behavioral-fail-missing-{str(uuid.uuid4())[:8]}"
            )

        errors = []
        connections_verified = 0

        # Scan active schemas and ensure they are connected to backend services
        schema_nodes = [nid for nid, n in graph.nodes.items() if n.node_type == NodeType.SCHEMA_NODE]
        for sn in schema_nodes:
            # Ensure there exists at least one SERVICE_NODE with an edge relation of 'binds_schema' targeting this schema
            incoming = graph.get_incoming_edges(sn)
            has_service_binding = any(
                e.relation == "binds_schema" and graph.nodes[e.source_id].node_type == NodeType.SERVICE_NODE
                for e in incoming
            )
            if not has_service_binding:
                errors.append(f"Orphaned database schema '{sn}' has no binding service definition in topology.")
            else:
                connections_verified += 1

        # Scan active UI components and ensure their states are hooked to backend APIs
        ui_nodes = [nid for nid, n in graph.nodes.items() if n.node_type == NodeType.UI_NODE]
        for un in ui_nodes:
            # Verify UI nodes bind to STATE_NODE or call API
            outgoing = graph.get_outgoing_edges(un)
            
            # Simple layout or layout viewport components are bypass exceptions
            if "layout" in un.lower() or un == "ui_layout_root":
                continue
                
            has_state_binding = any(
                e.relation == "binds_state" and graph.nodes[e.target_id].node_type in (NodeType.STATE_NODE, NodeType.UI_STATE_NODE, NodeType.DATA_STATE_NODE)
                for e in outgoing
            )

            if not has_state_binding:
                errors.append(f"UI Component '{un}' is structurally orphaned: missing a binds_state edge connection.")
            else:
                connections_verified += 1

        # Scan state nodes and verify they call APIs
        state_nodes = [nid for nid, n in graph.nodes.items() if n.node_type in (NodeType.STATE_NODE, NodeType.UI_STATE_NODE, NodeType.DATA_STATE_NODE)]
        for stn in state_nodes:
            node = graph.nodes[stn]
            # Bypass root UI or layout states that don't require backend API connections
            if "root_ui" in stn.lower() or "layout" in stn.lower() or "ui_layout_root" in stn.lower():
                continue

            if node.node_type == NodeType.UI_STATE_NODE:
                # Pure local UI state node does not require any calls_api edge
                connections_verified += 1
                continue

            outgoing = graph.get_outgoing_edges(stn)
            has_api_call = any(
                e.relation == "calls_api" and graph.nodes[e.target_id].node_type == NodeType.API_NODE
                for e in outgoing
            )
            if not has_api_call:
                errors.append(f"State hook store '{stn}' is dead: does not calls_api to any server backend endpoint.")
            else:
                connections_verified += 1


        passed = len(errors) == 0
        reason = f"Workflow coherence verified successfully ({connections_verified} edge bindings validated)." if passed else f"Coherence errors: {errors}"
        evidence_key = f"ev-behavioral-pass-{str(uuid.uuid4())[:8]}" if passed else f"ev-behavioral-fail-{str(uuid.uuid4())[:8]}"

        # ── Phase 6A: Record oracle rejections to failure memory ──
        if not passed:
            ui_count = sum(1 for n in graph.nodes.values() if n.node_type == NodeType.UI_NODE)
            api_count = sum(1 for n in graph.nodes.values() if n.node_type == NodeType.API_NODE)
            for err in errors:
                record_failure(
                    FailureType.ORACLE_REJECTION,
                    Severity.WARNING,
                    err,
                    project_id=project_id,
                    component="behavioral_oracle",
                    node_type="BEHAVIORAL",
                    ui_nodes=ui_count,
                    api_nodes=api_count,
                )

        return OracleResult(
            passed=passed,
            reason=reason,
            metrics={"connections_verified": connections_verified, "coherence_errors": len(errors)},
            evidence_key=evidence_key
        )
