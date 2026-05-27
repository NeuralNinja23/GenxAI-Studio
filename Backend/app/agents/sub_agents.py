# app/agents/sub_agents.py
"""
V4 Cognitive Faculty System — Stage 6: Minimal Cognition

Defines the clean-room cognitive faculties:
- Victoria
- Derek
- Luna
- Reggie
- Marcus

All faculties operate strictly inside the
non-authoritative mutation space.

Marcus acts purely to emit governance advisory signals.
"""

from typing import Any, Dict, List, Optional
import uuid

from app.cognition.patch_ir import PatchIR
from app.cognition.branch import BranchState
from app.models.runtime_models import MutationTier


class VictoriaUIFaculty:
    """
    Victoria:
    Suggests structural UI mutations and layout evolution paths.

    IMPORTANT:
    - Never assumes specific application archetypes
    - Never hardcodes dashboard/page/component identities
    - Operates purely on topology-discovered renderable nodes
    """

    @staticmethod
    def propose_mutations(
        branch: BranchState,
        description: str,
    ) -> List[PatchIR]:

        graph = branch.topology_graph

        # Discover renderable UI nodes dynamically
        ui_nodes = [
            node_id
            for node_id, node in graph.nodes.items()
            if node.node_type.value == "UI_NODE"
        ]

        proposals: List[PatchIR] = []

        # No UI exists yet → create emergent root UI
        if not ui_nodes:

            root_ui_id = f"root_ui_{uuid.uuid4().hex[:6]}"

            proposals.append(
                PatchIR(
                    patch_id=f"vic-ui-root-{uuid.uuid4().hex[:6]}",
                    target_node_id=root_ui_id,
                    mutation_tier=MutationTier.STRUCTURAL_UI,
                    action="ADD_NODE",
                    node_data={
                        "node_type": "UI_NODE",
                        "properties": {
                            "component_name": "RootView",
                            "layout_style": "adaptive",
                            "generated": True,
                            "description": description,
                            "is_root": True,
                        },
                    },
                )
            )

            return proposals

        # Mutate existing discovered UI nodes
        for target_ui in ui_nodes:

            proposals.append(
                PatchIR(
                    patch_id=f"vic-ui-{uuid.uuid4().hex[:6]}",
                    target_node_id=target_ui,
                    mutation_tier=MutationTier.STRUCTURAL_UI,
                    action="MODIFY_NODE",
                    node_data={
                        "properties": {
                            "layout_style": "adaptive_grid",
                            "semantic_intent": description,
                            "enhanced_by_victoria": True,
                        }
                    },
                )
            )

        return proposals


class DerekAPIFaculty:
    """
    Derek:
    Suggests API routes, backend services,
    and interaction flows.
    """

    @staticmethod
    def propose_mutations(
        branch: BranchState,
        description: str,
    ) -> List[PatchIR]:

        api_id = f"api_node_{uuid.uuid4().hex[:6]}"

        return [
            PatchIR(
                patch_id=f"derek-api-{uuid.uuid4().hex[:6]}",
                target_node_id=api_id,
                mutation_tier=MutationTier.BEHAVIORAL,
                action="ADD_NODE",
                node_data={
                    "node_type": "API_NODE",
                    "properties": {
                        "route_path": "/api/v1/resource",
                        "method": "GET",
                        "generated": True,
                        "description": description,
                    }
                },
            )
        ]


class LunaSchemaFaculty:
    """
    Luna:
    Suggests database entities,
    schemas,
    and relationships.
    """

    @staticmethod
    def propose_mutations(
        branch: BranchState,
        description: str,
    ) -> List[PatchIR]:

        schema_id = f"schema_node_{uuid.uuid4().hex[:6]}"

        return [
            PatchIR(
                patch_id=f"luna-db-{uuid.uuid4().hex[:6]}",
                target_node_id=schema_id,
                mutation_tier=MutationTier.TOPOLOGY,
                action="ADD_NODE",
                node_data={
                    "node_type": "SCHEMA_NODE",
                    "properties": {
                        "entity_name": "GeneratedEntity",
                        "fields": [
                            {
                                "name": "id",
                                "type": "str",
                                "required": True,
                            },
                            {
                                "name": "title",
                                "type": "str",
                                "required": True,
                            },
                            {
                                "name": "created_at",
                                "type": "datetime",
                                "required": True,
                            },
                        ],
                        "generated": True,
                        "description": description,
                    }
                },
            )
        ]


class ReggieWorkflowFaculty:
    """
    Reggie:
    Suggests workflow node flows
    and state machine transitions.
    """

    @staticmethod
    def propose_mutations(
        branch: BranchState,
        description: str,
    ) -> List[PatchIR]:

        workflow_id = f"workflow_{uuid.uuid4().hex[:6]}"

        return [
            PatchIR(
                patch_id=f"reggie-wf-{uuid.uuid4().hex[:6]}",
                target_node_id=workflow_id,
                mutation_tier=MutationTier.TOPOLOGY,
                action="ADD_NODE",
                node_data={
                    "node_type": "WORKFLOW_NODE",
                    "properties": {
                        "workflow_name": "GeneratedWorkflow",
                        "states": [
                            "IDLE",
                            "PROCESSING",
                            "COMPLETED",
                            "FAILED",
                        ],
                        "generated": True,
                        "description": description,
                    }
                },
            )
        ]


class MarcusGovernanceAnalyst:
    """
    Marcus:
    The Conscience, not the Ruler.

    Emits soft advisory signals routed strictly
    through the AttentionRouter.

    Marcus has ZERO authority to:
    - modify graphs
    - write files
    - approve transactions
    """

    @staticmethod
    def analyze_governance(
        branch: BranchState,
        drift_severity: str = "CLEAN",
    ) -> Dict[str, Any]:
        """
        Analyze branch convergence profile
        and failure similarity.

        Emits advisory values
        to influence the AttentionRouter.
        """

        modifier = 1.0
        warnings: List[str] = []
        is_stable = True

        # ─────────────────────────────────────────
        # 1. Repulsion Warning
        # ─────────────────────────────────────────

        if branch.repulsion_score > 0.6:

            modifier *= 0.5

            warnings.append(
                f"Branch '{branch.branch_id}' "
                f"displays severe structural proximity "
                f"to historical failures."
            )

            is_stable = False

        # ─────────────────────────────────────────
        # 2. Entropy Oscillation Check
        # ─────────────────────────────────────────

        if len(branch.entropy_history) >= 3:

            h = branch.entropy_history

            if h[-1] > h[-2] and h[-2] < h[-3]:

                modifier *= 0.7

                warnings.append(
                    "Oscillation detected in "
                    "branch entropy history."
                )

                is_stable = False

        # ─────────────────────────────────────────
        # 3. Drift Severity
        # ─────────────────────────────────────────

        if drift_severity in ["SEVERE", "CRITICAL"]:

            modifier *= 0.2

            warnings.append(
                f"Workspace drift is '{drift_severity}'. "
                f"Extreme risk of branch invalidation."
            )

            is_stable = False

        return {
            "branch_id": branch.branch_id,
            "marcus_advisory_modifier": modifier,
            "warnings": warnings,
            "is_stable": is_stable,
        }