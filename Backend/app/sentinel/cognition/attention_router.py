# app/cognition/attention_router.py
"""
V4 Bounded Cognition — Stage 6: Minimal Cognition
Implements the AttentionRouter.
Budget allocation and branch prioritization.
"""

from typing import List, Tuple, Dict
from app.sentinel.cognition.branch import BranchState

class AttentionRouter:
    """
    Manages bounded adaptive search resources by ranking and filtering active branch states.
    """

    def __init__(self, max_branches: int = 5):
        self.max_branches = max_branches

    @staticmethod
    def calculate_branch_weight(
        branch: BranchState
    ) -> float:
        """
        Assign an attention weight to a candidate universe.
        Refactored to prioritize execution correctness using verifications and goal completion.
        """
        from app.sentinel.verification.verification_gate import SentinelTopologyVerifier
        result = SentinelTopologyVerifier.verify(branch.topology_graph)

        # Build Score: dependency & schema checks average
        build_score = (result.dependency_graph_survival + result.schema_survival) / 2.0

        # Runtime Score: routing & state average
        runtime_score = (result.route_survival + result.state_survival) / 2.0

        # Topology Score
        topology_score = result.topology_survival

        # Repulsion penalty capped to prevent branch collapse
        repulsion_factor = max(0.25, 1.0 - min(branch.repulsion_score, 1.0))

        # Novelty/Entropy Score (closer to 0 change at final stages is better)
        if len(branch.entropy_history) >= 2:
            slope = abs(branch.entropy_history[-1] - branch.entropy_history[-2])
            novelty_score = 1.0 - min(slope, 1.0)
        else:
            novelty_score = 0.5

        # Refactored weights: Build=0.45, Runtime=0.35, Topology=0.10, Repulsion=0.05, Novelty=0.05
        w_build = 0.45
        w_runtime = 0.35
        w_topology = 0.10
        w_repulsion = 0.05
        w_novelty = 0.05

        # Calculate raw score
        raw_score = (
            (w_build * build_score) +
            (w_runtime * runtime_score) +
            (w_topology * topology_score) +
            (w_repulsion * repulsion_factor) +
            (w_novelty * novelty_score)
        )

        from app.core.logging import log

        # Evaluate repulsion gating exactly once per cycle
        if not getattr(branch, "_repulsion_checked", False):
            branch._repulsion_checked = True
            from app.sentinel.failure_memory.failure_geometry import FailureGeometry
            import numpy as np

            # Calculate mutation tier for branch topology
            def get_mutation_tier(graph):
                from app.models.runtime_models import MutationTier
                from app.sentinel.topology.node_types import NodeType
                max_t = MutationTier.COSMETIC
                for node in graph.nodes.values():
                    t_val = MutationTier.BEHAVIORAL
                    if node.node_type == NodeType.UI_NODE:
                        t_val = MutationTier.STRUCTURAL_UI
                    elif node.node_type in [NodeType.API_NODE, NodeType.ROUTE_NODE, NodeType.SCHEMA_NODE]:
                        t_val = MutationTier.TOPOLOGY
                    if t_val.value > max_t.value:
                        max_t = t_val
                return max_t.value if hasattr(max_t, 'value') else int(max_t)

            mutation_tier = get_mutation_tier(branch.topology_graph)
            candidate_vec = FailureGeometry.encode_state(
                failures=result.failures,
                graph=branch.topology_graph,
                mutation_tier=mutation_tier
            )

            # ── PRIORITY-0.5 INSTRUMENTATION: Prove vector collapse ──────────────
            log("PATCH_DEBUG", (
                f"[CANDIDATE_VEC] branch={branch.branch_id[:8]} "
                f"nodes={len(branch.topology_graph.nodes)} "
                f"edges={len(branch.topology_graph.edges)} "
                f"failures={len(result.failures)} "
                f"vec={candidate_vec.round(4).tolist()}"
                ))

            fg = FailureGeometry()
            records = fg.mal.load_repulsion_records()

            current_failures = len(result.failures)
            decision = "ALLOW"
            similarity_to_log = 0.0
            hist_fails_to_log = 0

            prune_match = None
            allow_match = None
            max_sim = 0.0
            matched_hist_fails = 0

            matched_hist_vec = None

            for rec in records:
                hist_vec = rec[1]
                hist_fails = rec[10] if rec[10] is not None else 0
                if hist_vec is not None and hist_vec.shape == candidate_vec.shape:
                    similarity = float(np.dot(candidate_vec, hist_vec))
                    if similarity >= 0.85:
                        if current_failures >= hist_fails:
                            if prune_match is None or similarity > prune_match[0]:
                                prune_match = (similarity, hist_fails)
                        else:
                            if allow_match is None or similarity > allow_match[0]:
                                allow_match = (similarity, hist_fails)
                    if similarity > max_sim:
                        max_sim = similarity
                        matched_hist_fails = hist_fails
                        matched_hist_vec = hist_vec

            if prune_match:
                decision = "PRUNE"
                similarity_to_log = prune_match[0]
                hist_fails_to_log = prune_match[1]
                branch.is_pruned = True
            elif allow_match:
                decision = "ALLOW"
                similarity_to_log = allow_match[0]
                hist_fails_to_log = allow_match[1]
            else:
                decision = "ALLOW"
                similarity_to_log = max_sim
                hist_fails_to_log = matched_hist_fails

            import logging
            logger = logging.getLogger("sentinel")
            logger.info(
                "[REPULSION_DIAGNOSTICS] "
                f"branch={branch.branch_id} "
                f"similarity={similarity_to_log:.4f} "
                f"novelty={novelty_score:.4f}"
            )
            logger.info(
                f"candidate_vector={candidate_vec.tolist()}"
            )
            logger.info(
                f"historical_vector={matched_hist_vec.tolist() if matched_hist_vec is not None else []}"
            )

            log("COGNITION", (
                f"[REPULSION_GATE] similarity={similarity_to_log:.4f} "
                f"historical_failures={hist_fails_to_log} "
                f"current_failures={current_failures} "
                f"decision={decision}"
            ))

        # Linear Delta Alpha modifier
        alpha_prev = getattr(branch, "previous_attention_weight", 1.0)
        delta_alpha = raw_score - alpha_prev
        delta_alpha_modifier = 1.0 + (delta_alpha * 0.2)

        # Multiply raw weight by goal completion rate (default to 1.0 if not present)
        goal_completion_rate = getattr(branch, "goal_completion_rate", 1.0)

        # Apply Delta Alpha modifier and goal completion rate modifier
        final_weight = float(max(raw_score * delta_alpha_modifier * goal_completion_rate, 0.01))

        log("COGNITION", (
            f"[REPULSION-VERIFY] branch={branch.branch_id[:8]} "
            f"build_score={build_score:.4f} "
            f"runtime_score={runtime_score:.4f} "
            f"topology_score={topology_score:.4f} "
            f"repulsion_factor={repulsion_factor:.4f} "
            f"novelty_score={novelty_score:.4f} "
            f"goal_completion={goal_completion_rate:.4f} "
            f"final_weight={final_weight:.4f}"
        ))
        return final_weight

    def route_attention(self, branches: List[BranchState]) -> List[BranchState]:
        """
        Scores all active branches and updates their attention weights.
        Sorts the list in descending order of attention weights.
        """
        for branch in branches:
            # Save the current attention weight to previous_attention_weight before re-calculating
            branch.previous_attention_weight = branch.attention_weight

            branch.attention_weight = self.calculate_branch_weight(branch)

        # Sort branches by attention weight in descending order
        branches.sort(key=lambda b: b.attention_weight, reverse=True)
        return branches

    def prune_to_budget(self, branches: List[BranchState]) -> Tuple[List[BranchState], List[BranchState]]:
        """
        Enforce the maximum active branch budget.
        Returns a tuple of (kept_branches, pruned_branches).
        """
        scored_branches = self.route_attention(branches)

        kept = scored_branches[:self.max_branches]
        pruned = scored_branches[self.max_branches:]

        # Mark pruned branches
        for b in pruned:
            b.is_pruned = True

        return kept, pruned
