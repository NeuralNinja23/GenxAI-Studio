# app/tools/__init__.py
"""
Tools Module - The SINGLE SOURCE OF TRUTH

Architecture:
- tools.py: 40 tool definitions (ID, function, capabilities, phases)
- registry.py: Simple lookup/run interface
"""

# The consolidated tool registry
from .tools import (
    TOOLS,
    Capability,
    ToolDefinition,
    get_tool,
    get_all_tools,
    get_tools_for_phase,
    get_pre_step_tools,
    get_post_step_tools,
    run_tool,
)

# Legacy-compatible imports
from .registry import get_available_tools

__all__ = [
    # Tools registry (NEW - single source of truth)
    "TOOLS",
    "Capability",
    "ToolDefinition",
    "get_tool",
    "get_all_tools",
    "get_tools_for_phase",
    "get_pre_step_tools",
    "get_post_step_tools",
    "run_tool",
    # Legacy
    "get_available_tools",
]

