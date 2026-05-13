# agents.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict

from .tool_binding import ToolBinding, ToolResult


@dataclass(frozen=True)
class AgentResult:
    success: bool
    output: Any
    error: str | None
    metadata: Dict[str, Any]


class Agent:
    """
    Execution agent.

    Rules:
    - No retries
    - No planning
    - No autonomy
    - No hidden loops
    """

    def __init__(self, name: str, tools: ToolBinding):
        self._name = name
        self._tools = tools

    def act(self, instruction: Dict[str, Any]) -> AgentResult:
        """
        Execute a single instruction.

        instruction format:
        {
            "tool": str,
            "args": dict
        }
        """

        tool_name = instruction.get("tool")
        tool_args = instruction.get("args", {})

        if not tool_name:
            return AgentResult(
                success=False,
                output=None,
                error="No tool specified in instruction",
                metadata={"agent": self._name},
            )

        result: ToolResult = self._tools.execute(tool_name, **tool_args)

        return AgentResult(
            success=result.success,
            output=result.output,
            error=result.error,
            metadata={
                "agent": self._name,
                "tool": tool_name,
                "duration_ms": result.duration_ms,
            },
        )
