# app/sentinel/experience/state_transition.py
"""
Canonical wrappers and observational comparators for the Sentinel Experience Repository & Transition Ledger (S-0.10).
"""

from typing import List, Dict, Any, Optional

class StateSnapshot:
    """Represents the observed state of a workspace at a specific point in time."""
    def __init__(
        self,
        failures: List[Dict[str, Any]],
        oracle: float,
        verification_summary: Dict[str, Any]
    ):
        self.failures = failures
        self.oracle = oracle
        self.verification_summary = verification_summary

    def to_dict(self) -> Dict[str, Any]:
        return {
            "failures": self.failures,
            "oracle": self.oracle,
            "verification_summary": self.verification_summary
        }


class IntentAction:
    """Represents the actions, parameters, and intent of a repair cycle execution."""
    def __init__(
        self,
        target_file: Optional[str],
        scope: Optional[str],
        repair_mode: Optional[str],
        instruction: Optional[str],
        prompt: Optional[str],
        context_metadata: Dict[str, Any]
    ):
        self.target_file = target_file
        self.scope = scope
        self.repair_mode = repair_mode
        self.instruction = instruction
        self.prompt = prompt
        self.context_metadata = context_metadata

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_file": self.target_file,
            "scope": self.scope,
            "repair_mode": self.repair_mode,
            "instruction": self.instruction,
            "prompt": self.prompt,
            "context_metadata": self.context_metadata
        }


class StateTransition:
    """Represents a complete, chronologically-chained state transition (Before State -> Action -> After State)."""
    def __init__(
        self,
        transition_id: str,
        parent_transition_id: Optional[str],
        cycle_id: str,
        workspace_id: str,
        attempt_number: int,
        workspace_hash: str,
        before_state: StateSnapshot,
        action: IntentAction,
        after_state: StateSnapshot,
        before_source: Optional[str] = None,
        after_source: Optional[str] = None,
        diff: Optional[str] = None,
        compiler_output: Optional[str] = None,
        bundler_output: Optional[str] = None,
        runtime_output: Optional[str] = None,
        render_output: Optional[str] = None
    ):
        self.transition_id = transition_id
        self.parent_transition_id = parent_transition_id
        self.cycle_id = cycle_id
        self.workspace_id = workspace_id
        self.attempt_number = attempt_number
        self.workspace_hash = workspace_hash
        self.before_state = before_state
        self.action = action
        self.after_state = after_state
        self.before_source = before_source
        self.after_source = after_source
        self.diff = diff
        self.compiler_output = compiler_output
        self.bundler_output = bundler_output
        self.runtime_output = runtime_output
        self.render_output = render_output

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "parent_transition_id": self.parent_transition_id,
            "cycle_id": self.cycle_id,
            "workspace_id": self.workspace_id,
            "attempt_number": self.attempt_number,
            "workspace_hash": self.workspace_hash,
            "before_state": self.before_state.to_dict(),
            "action": self.action.to_dict(),
            "after_state": self.after_state.to_dict(),
            "before_source": self.before_source,
            "after_source": self.after_source,
            "diff": self.diff,
            "compiler_output": self.compiler_output,
            "bundler_output": self.bundler_output,
            "runtime_output": self.runtime_output,
            "render_output": self.render_output
        }


# ─────────────────────────────────────────────────────────────
# Observational Comparators
# ─────────────────────────────────────────────────────────────

class FailureComparator:
    """Computes exact diffs between two failure fingerprint sets."""
    
    @staticmethod
    def _make_key(f: Dict[str, Any]) -> tuple:
        return (
            f.get("failure_type", "UNKNOWN"),
            str(f.get("file", f.get("file_path", "None")))
        )

    @classmethod
    def compare(
        cls,
        before_failures: List[Dict[str, Any]],
        after_failures: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Identifies resolved and newly introduced failures.
        Returns:
            {
                "resolved": List[Dict[str, Any]],
                "introduced": List[Dict[str, Any]],
                "net_change": int
            }
        """
        before_map = {cls._make_key(f): f for f in before_failures}
        after_map = {cls._make_key(f): f for f in after_failures}

        before_keys = set(before_map.keys())
        after_keys = set(after_map.keys())

        resolved_keys = before_keys - after_keys
        introduced_keys = after_keys - before_keys

        resolved = [before_map[k] for k in resolved_keys]
        introduced = [after_map[k] for k in introduced_keys]

        return {
            "resolved": resolved,
            "introduced": introduced,
            "net_change": len(after_failures) - len(before_failures)
        }


class StateComparator:
    """Computes basic score deltas of oracle state evaluations."""

    @staticmethod
    def compare(before_oracle: float, after_oracle: float) -> float:
        """Returns the numerical change (after - before). Negative means improvement."""
        return after_oracle - before_oracle


class VerificationComparator:
    """Compares raw logs and identifies changes in warnings, errors, and log size."""

    @staticmethod
    def compare(before_output: Optional[str], after_output: Optional[str]) -> Dict[str, Any]:
        before = before_output or ""
        after = after_output or ""
        
        return {
            "changed": before != after,
            "before_length": len(before),
            "after_length": len(after),
            "delta_length": len(after) - len(before)
        }
