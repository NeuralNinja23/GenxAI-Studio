# app/cognition/constraint_engine.py
"""
V4 Bounded Cognition — Stage 6: Minimal Cognition
Implements the Constraint Engine (the laws of physics inside Sentinel).
Validates topological mutations against hard constraints and blocks illegal Tier 5 operations.
"""

from typing import List
from pydantic import BaseModel, Field
from app.sentinel.cognition.patch_ir import PatchIR
from app.sentinel.directives import IntentField
from app.models.runtime_models import MutationTier

class ConstraintValidationResult(BaseModel):
    passed: bool
    violations: List[str] = Field(default_factory=list)


class ConstraintEngine:
    """
    Enforces the logical laws of physics in the cognitive navigation space.
    Strictly non-cognitive: applies logical invariants to filter and reject invalid candidate mutations.
    """

    FORBIDDEN_KEYWORDS = [
        "execution_kernel", "leases", "transaction_engine", "drift_detection",
        "reconstruction", "reality_sync", "substrate_manager", "oracle",
        "evidence_registry", "leases.py", "execution_kernel.py", "transaction_engine.py"
    ]

    @staticmethod
    def validate_mutation(patch: PatchIR, intent: IntentField) -> ConstraintValidationResult:
        """
        Validate a proposed PatchIR against structural bounds, invariants, and MutationTiers.
        """
        violations = []

        # 1. Hard block Tier 5 mutations
        if patch.mutation_tier == MutationTier.FORBIDDEN:
            violations.append("Illegal Tier 5 (Forbidden) Mutation class attempted.")

        # 2. Block direct kernel-level key modifications
        target_lower = patch.target_node_id.lower()
        if any(keyword in target_lower for keyword in ConstraintEngine.FORBIDDEN_KEYWORDS):
            violations.append(f"Mutation target '{patch.target_node_id}' infringes on the Immutable Runtime Kernel.")

        # Check payload data for kernel-level keyword insertion attempts
        if patch.node_data:
            for k, v in patch.node_data.items():
                if isinstance(v, str) and any(keyword in v.lower() for keyword in ConstraintEngine.FORBIDDEN_KEYWORDS):
                    violations.append(f"Forbidden system keyword detected in property '{k}': '{v}'")

        # 3. Validate against IntentField invariants
        if intent and intent.invariants:
            for invariant in intent.invariants:
                # Basic invariant enforcement: If the invariant says "No circular imports" or "Must have auth",
                # we can simulate checking it against the proposed patch configuration
                inv_lower = invariant.lower()
                if "auth" in inv_lower and patch.action == "REMOVE_NODE" and "auth" in target_lower:
                    violations.append(f"Violation of invariant: Cannot remove security boundary node '{patch.target_node_id}' ({invariant}).")
                if "read-only" in inv_lower and patch.action == "UPDATE_NODE" and "readonly" in target_lower:
                    violations.append(f"Violation of invariant: Modification of read-only component '{patch.target_node_id}' is prohibited.")

        # 4. Validate against IntentField constraints
        if intent and hasattr(intent, "constraints") and intent.constraints:
            for constraint in intent.constraints:
                if constraint.severity == "HARD":
                    # Check if the mutation violates the constraint target bounds
                    if constraint.validation_target.upper() == "DB" and patch.mutation_tier != MutationTier.TOPOLOGY:
                        if "database" in target_lower or "schema" in target_lower:
                            violations.append(f"Hard constraint violation: Database mutations must belong to Tier 4 Topology Mutation ({constraint.description}).")

        # 5. Validate against workflow state legality
        if intent and intent.workflow_legality:
            for rule in intent.workflow_legality:
                if patch.action == "ADD_EDGE" and patch.edge_data:
                    source = patch.edge_data.get("source")
                    target = patch.edge_data.get("target")
                    if source and target:
                        # If a forbidden state transition is attempted
                        for forbidden in rule.forbidden_states:
                            if source == forbidden or target == forbidden:
                                violations.append(f"Forbidden transition state detected in edge {source} -> {target} under workflow '{rule.workflow_id}'.")

        return ConstraintValidationResult(
            passed=len(violations) == 0,
            violations=violations
        )
