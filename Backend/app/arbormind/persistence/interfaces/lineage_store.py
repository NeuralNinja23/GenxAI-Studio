# persistence/interfaces/lineage_store.py

from __future__ import annotations
from typing import Optional, Iterable, Dict
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class LineageNodeRecord:
    lineage_id: str
    parent_lineage_id: Optional[str]
    execution_id: str
    failure_fingerprint_id: str
    directive_delta: Dict
    timestamp: datetime


class LineageStore:
    """
    Persistence contract for Φ trajectories (Universe of Trees).
    """

    def add_node(self, node: LineageNodeRecord) -> None:
        raise NotImplementedError

    def get(self, lineage_id: str) -> Optional[LineageNodeRecord]:
        raise NotImplementedError

    def ancestry(self, lineage_id: str) -> Iterable[LineageNodeRecord]:
        raise NotImplementedError
