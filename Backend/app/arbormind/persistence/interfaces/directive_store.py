# persistence/interfaces/directive_store.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime


@dataclass(frozen=True)
class CognitiveDirectiveSnapshot:
    """
    Immutable record of Ω at a specific execution boundary.
    """

    directive_id: str
    execution_id: str
    lineage_id: str

    allowed_mutations: List[str]
    forbidden_mutations: List[str]

    attention_boosts: Dict[str, float]
    attention_penalties: Dict[str, float]

    derived_from_fingerprints: List[str]
    timestamp: datetime


class DirectiveStore:
    """
    Persistence contract for Ω snapshots.

    This store:
    - remembers constraints
    - never remembers decisions
    """

    def save(self, snapshot: CognitiveDirectiveSnapshot) -> None:
        raise NotImplementedError

    def load_by_execution(
        self, execution_id: str
    ) -> Optional[CognitiveDirectiveSnapshot]:
        raise NotImplementedError

    def history_by_lineage(
        self, lineage_id: str
    ) -> List[CognitiveDirectiveSnapshot]:
        raise NotImplementedError
