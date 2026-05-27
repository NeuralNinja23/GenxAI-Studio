# app/cognition/mutation_engine.py
"""
V4 Bounded Cognition — Stage 6: Minimal Cognition

Implements the MutationEngine.

Enforces event-driven mutation escapes,
completely avoiding continuous/perpetual self-editing.
"""

from typing import Any, Dict, List, Optional
import uuid

from app.cognition.patch_ir import PatchIR
from app.cognition.branch import BranchState
from app.models.runtime_models import MutationTier


class MutationEngine:
    """
    Coordinates event-driven topological escapes.

    Only active under:
    - entropy pressure
    - oracle blockage
    - convergence stagnation
    """

    @staticmethod
    def propose_escape_mutations(
        branch: BranchState,
        trigger_reason: str,
        oracle_feedback: Optional[Dict[str, Any]] = None,
    ) -> List[PatchIR]:
        """
        Generate localized topological mutation proposals (PatchIR)
        to escape from blockages/stagnation.
        """

        proposals: List[PatchIR] = []

        graph = branch.topology_graph

        # ─────────────────────────────────────────────
        # 1. Oracle Blockage Escape Trigger
        # ─────────────────────────────────────────────

        if trigger_reason == "ORACLE_BLOCK" and oracle_feedback:

            failed_oracles = oracle_feedback.get(
                "failed_oracles",
                []
            )

            for oracle in failed_oracles:

                oracle_name = oracle.get(
                    "name",
                    ""
                ).lower()

                message = oracle.get(
                    "message",
                    ""
                ).lower()

                # ─────────────────────────────────────
                # Topology / Import Failure
                # ─────────────────────────────────────

                if (
                    "topology" in oracle_name
                    or "import" in message
                ):

                    for node_id in graph.nodes:

                        if node_id.lower() in message:

                            proposals.append(
                                PatchIR(
                                    patch_id=f"escape-edge-{uuid.uuid4().hex[:6]}",
                                    target_node_id=node_id,
                                    mutation_tier=MutationTier.TOPOLOGY,
                                    action="ADD_EDGE",
                                    edge_data={
                                        "source": node_id,
                                        "target": (
                                            "auth_service"
                                            if "auth" in message
                                            else list(graph.nodes.keys())[0]
                                        ),
                                        "relation": "imports",
                                    },
                                )
                            )

                # ─────────────────────────────────────
                # Syntax Failure
                # ─────────────────────────────────────

                elif (
                    "syntax" in oracle_name
                    or "tsx" in message
                    or "jsx" in message
                ):

                    for node_id, node in graph.nodes.items():

                        if (
                            node.node_type.value == "UI_NODE"
                            and node_id.lower() in message
                        ):

                            proposals.append(
                                PatchIR(
                                    patch_id=f"escape-ui-{uuid.uuid4().hex[:6]}",
                                    target_node_id=node_id,
                                    mutation_tier=MutationTier.COSMETIC,
                                    action="UPDATE_NODE",
                                    node_data={
                                        "properties": {
                                            "layout_density": "comfortable",
                                            "alignment": "center",
                                        }
                                    },
                                )
                            )

                # ─────────────────────────────────────
                # Behavioral / API Failure
                # ─────────────────────────────────────

                elif (
                    "behavioral" in oracle_name
                    or "api" in message
                ):

                    for node_id, node in graph.nodes.items():

                        if node.node_type.value == "API_NODE":

                            proposals.append(
                                PatchIR(
                                    patch_id=f"escape-api-{uuid.uuid4().hex[:6]}",
                                    target_node_id=node_id,
                                    mutation_tier=MutationTier.BEHAVIORAL,
                                    action="UPDATE_NODE",
                                    node_data={
                                        "properties": {
                                            "timeout_ms": 5000,
                                            "retry_count": 3,
                                        }
                                    },
                                )
                            )

        # ─────────────────────────────────────────────
        # 2. Convergence Stagnation Trigger
        # ─────────────────────────────────────────────

        elif trigger_reason == "STAGNATION":

            # Dynamically discover UI nodes
            ui_nodes = [
                nid
                for nid, node in graph.nodes.items()
                if node.node_type.value == "UI_NODE"
            ]

            # No UI topology available
            if not ui_nodes:
                return proposals

            target_ui = ui_nodes[0]

            # Create escape state node
            proposals.append(
                PatchIR(
                    patch_id=f"escape-stagnation-{uuid.uuid4().hex[:6]}",
                    target_node_id="alert_notification_state",
                    mutation_tier=MutationTier.BEHAVIORAL,
                    action="ADD_NODE",
                    node_data={
                        "node_type": "STATE_NODE",
                        "properties": {
                            "store_name": "alerts",
                            "initial_state": {
                                "visible": False
                            },
                        },
                    },
                )
            )

            # Bind UI -> escape state
            if target_ui in graph.nodes:

                proposals.append(
                    PatchIR(
                        patch_id=f"escape-stagnation-edge-{uuid.uuid4().hex[:6]}",
                        target_node_id=target_ui,
                        mutation_tier=MutationTier.STRUCTURAL_UI,
                        action="ADD_EDGE",
                        edge_data={
                            "source": target_ui,
                            "target": "alert_notification_state",
                            "relation": "binds_state",
                        },
                    )
                )

        # ─────────────────────────────────────────────
        # 3. Default Safe Escape Patch
        # ─────────────────────────────────────────────

        if not proposals and graph.nodes:

            first_node = list(graph.nodes.keys())[0]

            proposals.append(
                PatchIR(
                    patch_id=f"escape-default-{uuid.uuid4().hex[:6]}",
                    target_node_id=first_node,
                    mutation_tier=MutationTier.COSMETIC,
                    action="UPDATE_NODE",
                    node_data={
                        "properties": {
                            "entropy_pressure_applied": True
                        }
                    },
                )
            )

        return proposals