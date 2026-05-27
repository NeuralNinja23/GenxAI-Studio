# app/oracles/topology_oracle.py
"""
V4 Topology Oracle — Stage 4: Oracle Layer

HARD Oracle enforcing graph consistency, dependency invariants, and routing legality.
"""

from pathlib import Path
from typing import Any
import json
import uuid

from app.core.logging import log
from app.oracles.base import BaseOracle, OracleResult
from app.topology.topology_version_manager import TopologyVersionManager
from app.topology.topology_validator import TopologyValidator

class TopologyOracle(BaseOracle):
    """
    Topology Engine Physics (HARD).
    Validates graph dependencies, cyclic routes, imports, and manifest congruence.
    """

    def __init__(self):
        super().__init__(name="topology_oracle", is_hard=True)

    async def validate(self, project_id: str, project_path: Path, cycle_ctx: Any) -> OracleResult:
        log("ORACLE", f"🔍 Running Topology Oracle graph checks on {project_id}")

        # ── 1. Graph Validity (Deterministic Physics Engine) ──
        graph = await TopologyVersionManager.get_active_topology(project_id)
        if not graph:
            return OracleResult(
                passed=False,
                reason="Topology consistency verification failed: no active topology graph exists.",
                evidence_key=f"ev-topology-fail-missing-{str(uuid.uuid4())[:8]}"
            )

        val_result = TopologyValidator.validate_graph(graph)
        if not val_result.passed:
            reasons = [f"{v.rule}: {v.reason}" for v in val_result.violations]
            return OracleResult(
                passed=False,
                reason=f"Graph cycle or connection violation detected: {reasons}",
                metrics={"violations_count": len(val_result.violations)},
                evidence_key=f"ev-topology-fail-cyclic-{str(uuid.uuid4())[:8]}"
            )

        # ── 2. Manifest Projection Congruence ───────────────
        ast_manifest_path = project_path / ".genx_ast_manifest.json"
        if not ast_manifest_path.exists():
            return OracleResult(
                passed=False,
                reason="Manifest congruence violation: active AST projection manifest missing from workspace.",
                evidence_key=f"ev-topology-fail-manifest-{str(uuid.uuid4())[:8]}"
            )

        try:
            with open(ast_manifest_path, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
            
            # Assert that the manifest graph hash aligns with active topology graph hash
            manifest_graph_hash = manifest_data.get("topology", {}).get("graph_hash")
            if manifest_graph_hash != graph.graph_hash:
                return OracleResult(
                    passed=False,
                    reason="Split-brain detected: disk AST manifest does not match database active topology graph hash.",
                    evidence_key=f"ev-topology-fail-drift-{str(uuid.uuid4())[:8]}"
                )
        except Exception as e:
            return OracleResult(
                passed=False,
                reason=f"Failed to verify AST manifest congruence: {e}",
                evidence_key=f"ev-topology-fail-corrupt-{str(uuid.uuid4())[:8]}"
            )

        passed_key = f"ev-topology-pass-{str(uuid.uuid4())[:8]}"

        return OracleResult(
            passed=True,
            reason="Graph is structurally sound, acyclic, and aligned with filesystem manifest.",
            metrics={"nodes_count": len(graph.nodes), "edges_count": len(graph.edges)},
            evidence_key=passed_key
        )
