# app/cognition/mutation_engine.py
"""
V4 Bounded Cognition — Stage 6: Minimal Cognition

Implements the MutationEngine.

Enforces event-driven mutation escapes,
completely avoiding continuous/perpetual self-editing.
"""

from typing import Any, Dict, List, Optional
import uuid

from app.sentinel.cognition.patch_ir import PatchIR
from app.sentinel.cognition.branch import BranchState
from app.models.runtime_models import MutationTier
from app.sentinel.failure_memory.failure_recorder import record_failure, FailureType, Severity


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

    @staticmethod
    async def critique_and_stabilize(
        prompt: str,
        system_prompt: str,
        branch: BranchState,
        intent: Any,
    ) -> List[PatchIR]:
        """
        Phase 7: Bounded Reflection Loops with Decay.
        Takes LLM prompt and context, queries LLM, validates output via ConstraintEngine.
        Retries up to STABILIZATION_RETRY_LIMIT (3) times with temperature decay.
        Falls back to a Tier 1 semantic collapse if budget is exhausted.
        """
        from app.llm.adapter import call_llm
        from app.sentinel.cognition.constraint_engine import ConstraintEngine
        from app.sentinel.cognition.patch_ir_normalizer import PatchIRNormalizer
        from app.sentinel.topology.projection_metrics import ProjectionMetrics
        from app.core.logging import log

        STABILIZATION_RETRY_LIMIT = 3
        # Phase 7: Temperature decay (0.8 -> 0.6 -> 0.4)
        temperatures = [0.8, 0.6, 0.4]

        metrics = ProjectionMetrics.get_instance()
        current_prompt = prompt
        graph = branch.topology_graph
        valid_node_ids = set(graph.nodes.keys())

        for attempt in range(STABILIZATION_RETRY_LIMIT):
            temp = temperatures[attempt]
            log("COGNITION", f"🔄 Critique Pass Attempt {attempt+1}/{STABILIZATION_RETRY_LIMIT} (temp={temp})")

            try:
                raw_response = await call_llm(
                    prompt=current_prompt,
                    system_prompt=system_prompt,
                    temperature=temp
                )
                patches = PatchIRNormalizer.normalize_patch_list(raw_response, valid_node_ids)

                # Validate against laws of physics
                all_passed = True
                failed_reasons = []

                for patch in patches:
                    validation = ConstraintEngine.validate_mutation(patch, intent)
                    if not validation.passed:
                        all_passed = False
                        failed_reasons.append(
                            f"Patch {patch.patch_id} on {patch.target_node_id} failed: " + 
                            " ".join(validation.violations)
                        )

                if all_passed:
                    if attempt > 0:
                        metrics.record_stabilization_success()
                    return patches

                # Reflection needed
                metrics.record_stabilization_attempt()
                metrics.increment_reflection_retries()

                log("COGNITION", f"⚠️ Proposal validation failed. Initiating reflection loop {attempt+1}.")
                
                critique_msg = (
                    "Your previous topological patch proposal failed constraints with the following errors:\n"
                    + "\n".join(f"- {r}" for r in failed_reasons)
                    + "\n\nPlease revise your topological patches to comply with these constraints."
                )

                current_prompt = f"{prompt}\n\n[SYSTEM CRITIQUE - ATTEMPT {attempt+1}]\n{critique_msg}"

            except Exception as e:
                log("COGNITION", f"❌ LLM failure during critique pass attempt {attempt+1}: {e}")

        # Phase 7: Semantic Collapse (revert to Tier 1)
        log("COGNITION", "⚠️ Reflection budget exhausted. Initiating fallback semantic collapse (Tier 1).")

        # ── Phase 6A: Record reflection exhaustion ────────────────────
        fallback_node = list(valid_node_ids)[0] if valid_node_ids else "root"
        record_failure(
            FailureType.REFLECTION_EXHAUSTION,
            Severity.ERROR,
            f"Reflection budget exhausted after {STABILIZATION_RETRY_LIMIT} attempts. "
            f"Collapsed to Tier 1 on node '{fallback_node}'.",
            component=system_prompt[:40] if system_prompt else "unknown_faculty",
            node_type="COGNITION",
        )
        
        return [
            PatchIR(
                patch_id=f"collapse-{uuid.uuid4().hex[:6]}",
                target_node_id=fallback_node,
                mutation_tier=MutationTier.COSMETIC,
                action="UPDATE_NODE",
                node_data={
                    "properties": {
                        "reflection_exhausted": True,
                        "entropy_pressure_applied": True
                    }
                }
            )
        ]