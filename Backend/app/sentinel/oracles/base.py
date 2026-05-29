# app/oracles/base.py
"""
V4 Oracle Base Definitions — Stage 4: Oracle Layer

Defines the abstract interface for all V4 oracles.
Oracles function as deterministic verification physics.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class OracleResult(BaseModel):
    """The formal syntactic/structural validation outcome of an oracle run."""
    passed: bool
    reason: str
    metrics: Dict[str, Any] = Field(default_factory=dict)
    evidence_key: Optional[str] = None


class BaseOracle(ABC):
    """
    Abstract Base Oracle.
    All V4 verification physics engines inherit from this interface.
    """

    def __init__(self, name: str, is_hard: bool = True):
        self._name = name
        self._is_hard = is_hard

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_hard(self) -> bool:
        """If True, failure blocks transaction commits. If False, advisory only."""
        return self._is_hard

    @abstractmethod
    async def validate(self, project_id: str, project_path: Path, cycle_ctx: Any) -> OracleResult:
        """Perform validation and return a structured OracleResult."""
        pass
