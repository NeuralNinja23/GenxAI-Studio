# app/handlers/__init__.py
"""
Workflow step handlers - one function per workflow step.

Active Procedural Steps:
- system_integration: Deterministic Python wiring
"""
from .system_integration import step_system_integration

__all__ = [
    "step_system_integration",
]



