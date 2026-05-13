# tool_binding.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Dict
import time


@dataclass(frozen=True)
class ToolResult:
    success: bool
    output: Any
    error: str | None
    duration_ms: int


class ToolBinding:
    """
    Executes tools under strict ArborMind law.

    Rules:
    - One call only
    - No retries
    - No internal loops
    - No self-healing
    """

    def __init__(self, tools: Dict[str, Callable[..., Any]]):
        self._tools = tools

    def execute(self, tool_name: str, **kwargs) -> ToolResult:
        if tool_name not in self._tools:
            return ToolResult(
                success=False,
                output=None,
                error=f"Tool '{tool_name}' not registered",
                duration_ms=0,
            )

        tool = self._tools[tool_name]
        start = time.time()

        try:
            output = tool(**kwargs)
            duration = int((time.time() - start) * 1000)

            return ToolResult(
                success=True,
                output=output,
                error=None,
                duration_ms=duration,
            )

        except Exception as exc:
            duration = int((time.time() - start) * 1000)

            return ToolResult(
                success=False,
                output=None,
                error=str(exc),
                duration_ms=duration,
            )
