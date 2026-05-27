# app/runtime/execution_contracts.py
"""
V4 Execution Contracts — Stage 1: Freeze Runtime

Defines the hard structural preconditions that MUST hold before any
projection cycle is permitted to begin, and the mutation boundary rules
that govern what each Mutation Tier may affect.

Philosophy:
    Contracts are checked by the execution kernel before acquiring a lease.
    A failed contract is an absolute STOP — the cycle does not begin.
    No retry. No healing. The contract violation is recorded and the
    cognitive layer must propose a corrected mutation.

Mutation Tier enforcement:
    Tier 1 (Cosmetic)        — CSS/styling files only
    Tier 2 (Structural UI)   — React component trees and layout files
    Tier 3 (Behavioral)      — Logic, state, and API call files
    Tier 4 (Topology)        — Routes, DB schemas, service boundaries
    Tier 5 (Forbidden)       — Execution kernel, oracle hierarchy, substrate
                               ALWAYS BLOCKED. No exception path exists.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional, Set

from app.core.logging import log
from app.models.runtime_models import MutationTier
from app.substrate.substrate_manager import SubstrateManager


# ─────────────────────────────────────────────────────────────
# Allowed file patterns per mutation tier
# (additive: lower tiers are subsets of higher)
# ─────────────────────────────────────────────────────────────

# File glob suffixes allowed per tier
TIER_ALLOWED_EXTENSIONS: Dict[MutationTier, FrozenSet[str]] = {
    MutationTier.COSMETIC: frozenset({
        ".css", ".scss", ".less",
    }),
    MutationTier.STRUCTURAL_UI: frozenset({
        ".css", ".scss", ".less",
        ".tsx", ".jsx", ".ts", ".js",
    }),
    MutationTier.BEHAVIORAL: frozenset({
        ".css", ".scss", ".less",
        ".tsx", ".jsx", ".ts", ".js",
        ".py",
    }),
    MutationTier.TOPOLOGY: frozenset({
        ".css", ".scss", ".less",
        ".tsx", ".jsx", ".ts", ".js",
        ".py",
        ".json", ".yaml", ".yml",
        ".md",
    }),
    MutationTier.FORBIDDEN: frozenset(),  # Nothing allowed
}

# Path segments that are ABSOLUTELY forbidden at ALL tiers
ABSOLUTELY_FORBIDDEN_PATH_SEGMENTS: FrozenSet[str] = frozenset({
    "execution_kernel",
    "transaction_engine",
    "leases",
    "projection_snapshots",
    "workspace_snapshots",
    "drift_detection",
    "execution_contracts",
    "runtime_projection_validator",
    "oracles",
    "substrate_manager",
})


# ─────────────────────────────────────────────────────────────
# Contract result types
# ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ContractViolation:
    rule: str
    detail: str
    is_fatal: bool = True


@dataclass
class ContractCheckResult:
    passed: bool
    violations: List[ContractViolation] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_violation(self, rule: str, detail: str, fatal: bool = True) -> None:
        self.violations.append(ContractViolation(rule=rule, detail=detail, is_fatal=fatal))
        if fatal:
            self.passed = False

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)


# ─────────────────────────────────────────────────────────────
# Execution Contract Checker
# ─────────────────────────────────────────────────────────────

class ExecutionContracts:
    """
    Hard contract enforcement for projection cycle initiation.

    Called by execution_kernel.py before every projection cycle.
    Any failed contract is a cycle STOP — not a retry.
    """

    # ──────────────────────────────────────────────────────────
    # Primary entry point
    # ──────────────────────────────────────────────────────────

    @staticmethod
    async def verify_pre_cycle(
        project_id: str,
        project_path: Path,
        mutation_tier: MutationTier,
        proposed_writes: List[str],
        required_oracle_tiers: Optional[List[str]] = None,
    ) -> ContractCheckResult:
        """
        Verify all structural preconditions before a projection cycle may begin.

        Checks (in order, all must pass):
            1. Mutation tier is not FORBIDDEN
            2. Proposed write targets are legal for the mutation tier
            3. No write targets are absolutely forbidden kernel paths
            4. Substrate integrity is clean (no externally modified locked files)
            5. Required oracle tiers are specified (must match mutation tier)

        Args:
            project_id:             Project being mutated.
            project_path:           Absolute path to project workspace.
            mutation_tier:          Tier of the proposed mutation.
            proposed_writes:        List of relative paths the cycle intends to write.
            required_oracle_tiers:  Oracle validation tiers that will be run post-cycle.

        Returns:
            ContractCheckResult with passed=True if all checks pass.
        """
        result = ContractCheckResult(passed=True)

        # ── 1. Tier 5 absolute block ──────────────────────────
        if mutation_tier == MutationTier.FORBIDDEN:
            result.add_violation(
                rule="TIER5_FORBIDDEN",
                detail="Mutation Tier 5 (Forbidden) is unconditionally blocked. "
                       "No exception path exists. Targeting execution kernel, oracle "
                       "hierarchy, transaction systems, or substrate boundaries is "
                       "architecturally illegal.",
                fatal=True,
            )
            log("CONTRACT", f"⛔ TIER5 FORBIDDEN mutation blocked for {project_id}")
            return result  # Stop immediately — no further checks needed

        # ── 2. Validate proposed write targets against tier ───
        allowed_extensions = TIER_ALLOWED_EXTENSIONS.get(mutation_tier, frozenset())
        for rel_path in proposed_writes:
            ext = Path(rel_path).suffix.lower()
            if ext not in allowed_extensions:
                result.add_violation(
                    rule="TIER_EXTENSION_VIOLATION",
                    detail=f"File '{rel_path}' (extension '{ext}') is not permitted "
                           f"for Mutation Tier {mutation_tier.name}. "
                           f"Allowed extensions: {sorted(allowed_extensions)}",
                )

        # ── 3. Absolutely forbidden kernel paths ──────────────
        for rel_path in proposed_writes:
            normalized = rel_path.replace("\\", "/")
            for forbidden_segment in ABSOLUTELY_FORBIDDEN_PATH_SEGMENTS:
                if forbidden_segment in normalized:
                    result.add_violation(
                        rule="FORBIDDEN_KERNEL_PATH",
                        detail=f"Write target '{rel_path}' contains forbidden path segment "
                               f"'{forbidden_segment}'. Runtime kernel files are immutable "
                               f"and may never be targeted by any projection cycle.",
                        fatal=True,
                    )

        # ── 4. Substrate integrity ────────────────────────────
        for rel_path in proposed_writes:
            if SubstrateManager.is_forbidden_write_target(rel_path):
                result.add_violation(
                    rule="SUBSTRATE_WRITE_FORBIDDEN",
                    detail=f"Write target '{rel_path}' is a locked substrate file. "
                           f"Framework configuration files are immutable after workspace creation. "
                           f"This is a Tier 5 Forbidden Mutation.",
                    fatal=True,
                )

        is_clean, violations = await SubstrateManager.verify_integrity(project_id, project_path)
        if not is_clean:
            for v in violations:
                result.add_violation(
                    rule="SUBSTRATE_INTEGRITY_FAILURE",
                    detail=f"Substrate integrity check failed: {v}. "
                           f"A locked framework file was externally modified. "
                           f"The projection cycle cannot begin until the substrate is restored.",
                    fatal=True,
                )

        # ── 5. Oracle tier requirement ────────────────────────
        required_oracles = _required_oracles_for_tier(mutation_tier)
        provided_oracles = set(required_oracle_tiers or [])
        missing_oracles = required_oracles - provided_oracles

        if missing_oracles:
            result.add_violation(
                rule="MISSING_ORACLE_REQUIREMENT",
                detail=f"Mutation Tier {mutation_tier.name} requires oracle validation "
                       f"from: {sorted(required_oracles)}. "
                       f"Missing: {sorted(missing_oracles)}. "
                       f"All required hard oracles must be declared before cycle start.",
                fatal=True,
            )

        if result.passed:
            log("CONTRACT", f"✅ Pre-cycle contracts passed for {project_id} (tier={mutation_tier.name})")
        else:
            log("CONTRACT",
                f"⛔ Pre-cycle contracts FAILED for {project_id}: "
                f"{[v.rule for v in result.violations]}")

        return result

    # ──────────────────────────────────────────────────────────
    # Post-cycle commit guard
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def verify_pre_commit(
        oracle_results: Dict[str, Any],
        mutation_tier: MutationTier,
    ) -> ContractCheckResult:
        """
        Verify that all required hard oracles passed before committing a transaction.

        A single hard oracle failure blocks the commit permanently.
        The transaction must be rolled back and a corrected mutation proposed.

        Args:
            oracle_results:  Dict of oracle_name → result dict (must contain 'passed' key).
            mutation_tier:   Tier of the mutation being committed.

        Returns:
            ContractCheckResult with passed=True if commit is permitted.
        """
        result = ContractCheckResult(passed=True)
        required_oracles = _required_oracles_for_tier(mutation_tier)

        for oracle_name in required_oracles:
            oracle_result = oracle_results.get(oracle_name)
            if oracle_result is None:
                result.add_violation(
                    rule="MISSING_ORACLE_RESULT",
                    detail=f"Required hard oracle '{oracle_name}' has no result. "
                           f"Commit blocked: cannot claim success without verified evidence.",
                    fatal=True,
                )
            elif not oracle_result.get("passed", False):
                result.add_violation(
                    rule="HARD_ORACLE_FAILURE",
                    detail=f"Hard oracle '{oracle_name}' FAILED: "
                           f"{oracle_result.get('reason', 'no reason provided')}. "
                           f"Transaction commit is unconditionally blocked. "
                           f"Transaction must be rolled back.",
                    fatal=True,
                )

        return result


# ─────────────────────────────────────────────────────────────
# Tier → required oracle mapping
# ─────────────────────────────────────────────────────────────

def _required_oracles_for_tier(tier: MutationTier) -> Set[str]:
    """Return the set of hard oracle names required for a given mutation tier."""
    # Cosmetic: syntax only
    if tier == MutationTier.COSMETIC:
        return {"syntax_oracle"}

    # Structural UI: syntax + topology
    if tier == MutationTier.STRUCTURAL_UI:
        return {"syntax_oracle", "topology_oracle"}

    # Behavioral: syntax + topology + behavioral
    if tier == MutationTier.BEHAVIORAL:
        return {"syntax_oracle", "topology_oracle", "behavioral_oracle"}

    # Topology: full hard oracle suite
    if tier == MutationTier.TOPOLOGY:
        return {"syntax_oracle", "topology_oracle", "behavioral_oracle", "runtime_oracle"}

    # Forbidden: no oracle suite — should never reach here
    return set()
