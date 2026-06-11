"""
app/sentinel/config/oracle_policy.py

Oracle Policy Loader for the Atlas Repair Faculty (Phase 5).

Design decisions:
  - Weights are loaded from oracle_policy.json at startup, not hardcoded in Python.
  - compute_oracle always receives an OraclePolicy dependency — no module-level globals.
  - max_scope_for() enforces the MAX_SCOPE_BY_FAILURE_COUNT cap; the kernel calls this
    before passing scope to the projector.

Usage:
    policy = OraclePolicyLoader.load(Path("Backend/app/sentinel/config/oracle_policy.json"))
    loss   = compute_oracle(failures, policy)
    cap    = policy.max_scope_for(len(failures))   # RepairScope ceiling for this failure count
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.models.runtime_models import RepairScope


# ─────────────────────────────────────────────────────────────
# Domain types
# ─────────────────────────────────────────────────────────────

_SCOPE_ORDER = [
    RepairScope.COMPONENT,
    RepairScope.MODULE,
    RepairScope.FEATURE,
    RepairScope.WORKSPACE,
]


@dataclass
class OraclePolicy:
    """
    Loaded oracle policy.  All numeric weights and structural thresholds
    come exclusively from oracle_policy.json — never from source code.
    """
    weights:                    Dict[str, int]
    fallback_weight:            int
    scope_escalation_threshold: int
    scope_cap_thresholds:       List[Tuple[int, RepairScope]]  # sorted asc by max_failures
    default_max_scope:          RepairScope

    def max_scope_for(self, failure_count: int) -> RepairScope:
        """
        Return the maximum RepairScope allowed for this failure count.

        Walks thresholds in ascending order and returns the first
        max_scope where failure_count <= max_failures.
        Falls back to default_max_scope if none match.
        """
        for max_failures, max_scope in self.scope_cap_thresholds:
            if failure_count <= max_failures:
                return max_scope
        return self.default_max_scope

    def next_scope(self, current: RepairScope) -> Optional[RepairScope]:
        """
        Return the next escalation scope above current, or None if already
        at WORKSPACE (caller should emit RepairExhaustedSignal).
        """
        try:
            idx = _SCOPE_ORDER.index(current)
        except ValueError:
            return None
        next_idx = idx + 1
        if next_idx >= len(_SCOPE_ORDER):
            return None
        return _SCOPE_ORDER[next_idx]


# ─────────────────────────────────────────────────────────────
# Errors
# ─────────────────────────────────────────────────────────────

class InvalidOraclePolicyError(ValueError):
    """Raised when oracle_policy.json fails schema validation."""


# ─────────────────────────────────────────────────────────────
# Loader
# ─────────────────────────────────────────────────────────────

class OraclePolicyLoader:
    """Reads and validates oracle_policy.json; constructs OraclePolicy."""

    @staticmethod
    def load(path: Path) -> OraclePolicy:
        """
        Load and validate an oracle_policy.json file.

        Raises:
            FileNotFoundError: if path does not exist.
            InvalidOraclePolicyError: if schema is invalid.
        """
        if not path.exists():
            raise FileNotFoundError(f"oracle_policy.json not found at: {path}")

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise InvalidOraclePolicyError(f"Invalid JSON in oracle_policy.json: {exc}") from exc

        # ── Validate required top-level keys ──
        required = {"oracle_weights", "fallback_weight", "scope_escalation_threshold", "scope_cap"}
        missing = required - set(raw.keys())
        if missing:
            raise InvalidOraclePolicyError(
                f"oracle_policy.json is missing required keys: {sorted(missing)}"
            )

        weights = raw["oracle_weights"]
        if not isinstance(weights, dict) or not all(
            isinstance(k, str) and isinstance(v, (int, float)) for k, v in weights.items()
        ):
            raise InvalidOraclePolicyError(
                "oracle_weights must be a dict mapping str → number"
            )

        fallback = raw["fallback_weight"]
        if not isinstance(fallback, (int, float)):
            raise InvalidOraclePolicyError("fallback_weight must be a number")

        threshold = raw["scope_escalation_threshold"]
        if not isinstance(threshold, int) or threshold < 1:
            raise InvalidOraclePolicyError(
                "scope_escalation_threshold must be a positive integer"
            )

        # ── Parse scope_cap ──
        scope_cap = raw["scope_cap"]
        if not isinstance(scope_cap, dict):
            raise InvalidOraclePolicyError("scope_cap must be an object")

        cap_thresholds: List[Tuple[int, RepairScope]] = []
        for entry in scope_cap.get("thresholds", []):
            if "max_failures" not in entry or "max_scope" not in entry:
                raise InvalidOraclePolicyError(
                    "Each scope_cap threshold must have 'max_failures' and 'max_scope'"
                )
            try:
                scope = RepairScope(entry["max_scope"])
            except ValueError:
                raise InvalidOraclePolicyError(
                    f"Invalid max_scope value: '{entry['max_scope']}'. "
                    f"Must be one of: {[s.value for s in RepairScope]}"
                )
            cap_thresholds.append((int(entry["max_failures"]), scope))

        # Sort ascending by max_failures so max_scope_for() works correctly
        cap_thresholds.sort(key=lambda t: t[0])

        default_scope_raw = scope_cap.get("default_max_scope", "WORKSPACE")
        try:
            default_scope = RepairScope(default_scope_raw)
        except ValueError:
            raise InvalidOraclePolicyError(
                f"Invalid default_max_scope: '{default_scope_raw}'"
            )

        return OraclePolicy(
            weights={k: int(v) for k, v in weights.items()},
            fallback_weight=int(fallback),
            scope_escalation_threshold=int(threshold),
            scope_cap_thresholds=cap_thresholds,
            default_max_scope=default_scope,
        )


# ─────────────────────────────────────────────────────────────
# Oracle computation
# ─────────────────────────────────────────────────────────────

def compute_oracle(failures: list, policy: OraclePolicy) -> float:
    """
    Compute the weighted loss score for a list of FailureFingerprint objects.

    Oracle(V) = Σ (weight_i × 1) for each failure f_i.
    Unknown failure types use policy.fallback_weight.

    Args:
        failures:  List of FailureFingerprint (or any object with .failure_type: str).
        policy:    Loaded OraclePolicy — MUST be injected; never access LOSS_WEIGHTS directly.

    Returns:
        float weighted loss score. Higher = worse. 0.0 = no failures.
    """
    return float(
        sum(
            policy.weights.get(f.failure_type, policy.fallback_weight)
            for f in failures
        )
    )
