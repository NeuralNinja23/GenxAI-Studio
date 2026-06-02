# app/cognition/attention_router.py
"""
V4 Bounded Cognition — Stage 6: Minimal Cognition
Implements the AttentionRouter.
Budget allocation, branch prioritization, and indirect Marcus advisory routing.
"""

from typing import List, Tuple, Dict
from app.sentinel.cognition.branch import BranchState

class AttentionRouter:
    """
    Manages bounded adaptive search resources by ranking and filtering active branch states.
    Routes Marcus advisory signals strictly as soft multipliers.
    """

    def __init__(self, max_branches: int = 5):
        self.max_branches = max_branches

    @staticmethod
    def calculate_branch_weight(
        branch: BranchState,
        marcus_advisory_modifier: float = 1.0
    ) -> float:
        """
        Assign an attention weight to a candidate universe.
        $$\\text{Score} = (w_1 \\times \\text{RepulsionFactor} + w_2 \\times \\text{Convergence} + w_3 \\times \\text{Simplicity}) \\times \\text{MarcusModifier}$$
        """
        w1 = 0.5
        w2 = 0.3
        w3 = 0.2

        # 1. Repulsion penalty capped to prevent branch collapse
        repulsion_factor = max(0.25, 1.0 - min(branch.repulsion_score, 1.0))

        # 2. Convergence factor (closer to 0 change at final stages is better)
        if len(branch.entropy_history) >= 2:
            slope = abs(branch.entropy_history[-1] - branch.entropy_history[-2])
            convergence_factor = 1.0 - min(slope, 1.0)
        else:
            convergence_factor = 0.5

        # 3. Complexity penalty (simpler topologies are favored)
        node_count = len(branch.topology_graph.nodes)
        edge_count = len(branch.topology_graph.edges)
        complexity = (node_count + edge_count) / 100.0
        complexity_factor = 1.0 - min(complexity, 0.9)

        # Calculate raw score
        raw_score = (w1 * repulsion_factor) + (w2 * convergence_factor) + (w3 * complexity_factor)

        # Apply Marcus advisory modifier
        final_weight = float(max(raw_score * marcus_advisory_modifier, 0.01))

        from app.core.logging import log
        log("COGNITION", (
            f"[REPULSION-VERIFY] branch={branch.branch_id[:8]} "
            f"repulsion_score={branch.repulsion_score:.4f} "
            f"repulsion_factor={repulsion_factor:.4f} "
            f"convergence={convergence_factor:.4f} "
            f"complexity={complexity_factor:.4f} "
            f"marcus_mod={marcus_advisory_modifier:.4f} "
            f"final_weight={final_weight:.4f}"
        ))
        return final_weight

    def route_attention(self, branches: List[BranchState], marcus_modifiers: dict = None) -> List[BranchState]:
        """
        Scores all active branches and updates their attention weights.
        Sorts the list in descending order of attention weights.
        """
        if marcus_modifiers is None:
            marcus_modifiers = {}

        for branch in branches:
            modifier = branch.governance.get("modifier")
            if modifier is None:
                modifier = marcus_modifiers.get(branch.branch_id, 1.0)
            branch.attention_weight = self.calculate_branch_weight(branch, modifier)

        # Sort branches by attention weight in descending order
        branches.sort(key=lambda b: b.attention_weight, reverse=True)
        return branches

    def prune_to_budget(self, branches: List[BranchState], marcus_modifiers: dict = None) -> Tuple[List[BranchState], List[BranchState]]:
        """
        Enforce the maximum active branch budget.
        Returns a tuple of (kept_branches, pruned_branches).
        """
        scored_branches = self.route_attention(branches, marcus_modifiers)

        kept = scored_branches[:self.max_branches]
        pruned = scored_branches[self.max_branches:]

        # Mark pruned branches
        for b in pruned:
            b.is_pruned = True

        return kept, pruned
