# state.py

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid


class ExecutionStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    HALTED = "halted"


class FailureSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    FATAL = "fatal"


@dataclass
class StepResult:
    step_id: str
    output: Optional[Any]
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class FailureRecord:
    failure_id: str
    step_id: str
    reason: str
    severity: FailureSeverity
    context: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)


# CognitiveBranch: REMOVED from Phase 1.
# Canonical definition lives in phase_3/divergence_controller.py (control layer).
# Phase 1 = representation. Phase 3 = control. Control dominates.



@dataclass
class ExecutionState:
    """
    Canonical runtime state for ArborMind execution.

    IMPORTANT:
    - No retries
    - No hidden healing
    - Failures halt unless explicitly escalated by a higher authority
    """

    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: ExecutionStatus = ExecutionStatus.IDLE

    current_step: Optional[str] = None
    completed_steps: List[str] = field(default_factory=list)

    results: Dict[str, StepResult] = field(default_factory=dict)
    failures: List[FailureRecord] = field(default_factory=list)

    cognitive_branches: Dict[str, Any] = field(default_factory=dict)

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def mark_running(self, step_id: str) -> None:
        self.status = ExecutionStatus.RUNNING
        self.current_step = step_id
        self.updated_at = datetime.utcnow()

    def mark_completed(self, step_id: str, result: StepResult) -> None:
        self.results[step_id] = result
        self.completed_steps.append(step_id)
        self.current_step = None
        self.status = ExecutionStatus.COMPLETED
        self.updated_at = datetime.utcnow()

    def mark_failed(self, failure: FailureRecord) -> None:
        self.failures.append(failure)
        self.current_step = None
        self.status = ExecutionStatus.FAILED
        self.updated_at = datetime.utcnow()

    def halt(self) -> None:
        self.status = ExecutionStatus.HALTED
        self.current_step = None
        self.updated_at = datetime.utcnow()
