# app/orchestration/__init__.py
"""
V4 Orchestration Package

V3 phase-based orchestration has been permanently removed.

Remaining exports (runtime session management only):
- WorkflowStateManager  — MongoDB-backed workflow session state
- broadcast_to_project  — WebSocket broadcast utility
- BudgetManager         — API cost tracking

V4 execution will be provided by the Execution Kernel (Stage 1).
"""

from .state import WorkflowStateManager, CURRENT_MANAGERS, WORKFLOW_LOCK
from .utils import broadcast_to_project, pluralize
from .budget_manager import (
    BudgetManager,
    BudgetConfig,
    StepPolicy,
    get_budget_manager,
    reset_budget_manager,
)

__all__ = [
    # State management
    "WorkflowStateManager",
    "CURRENT_MANAGERS",
    "WORKFLOW_LOCK",
    # Broadcast utilities
    "broadcast_to_project",
    "pluralize",
    # Budget tracking
    "BudgetManager",
    "BudgetConfig",
    "StepPolicy",
    "get_budget_manager",
    "reset_budget_manager",
]
