# execution_adapter.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.orchestration.fast_orchestrator import FASTExecutor


# ═══════════════════════════════════════════════════════════════════════════════
# THE CONTRACT: ExecutionDirective
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ExecutionDirective:
    """
    The ONLY artifact ArborMind is allowed to send to FAST.

    Contract:
    - immutable
    - no branching
    - no alternatives
    - no retry metadata
    """

    execution_id: str
    tool: str
    parameters: Dict[str, Any]
    constraints: Dict[str, Any]
    timeout_s: int
    workspace_path: str 


@dataclass(frozen=True)
class ExecutionOutcome:
    """
    The ONLY artifact FAST is allowed to return to ArborMind.

    Contract:
    - success or failure
    - no opinions
    - no alternatives
    - no retry suggestions
    """

    success: bool
    result: Any
    error: str | None
    duration_ms: int


# ═══════════════════════════════════════════════════════════════════════════════
# THE ADAPTER: FastExecutionAdapter
# ═══════════════════════════════════════════════════════════════════════════════

class ExecutionAdapter:
    """
    ArborMind's interface to FAST.

    This adapter:
    - lives inside ArborMind (not FAST)
    - sends exactly one ExecutionDirective
    - receives exactly one ExecutionOutcome
    - never retries
    - never interprets
    - never mutates

    FAST is pure muscle.
    """

    def __init__(self, fast_executor: "FASTExecutor"):
        self._fast = fast_executor

    async def execute(self, directive: ExecutionDirective) -> ExecutionOutcome:
        """
        Execute once. Return outcome. Done.
        """
        return await self._fast.execute_once(
            tool=directive.tool,
            parameters=directive.parameters,
            constraints=directive.constraints,
            timeout=directive.timeout_s,
        )
