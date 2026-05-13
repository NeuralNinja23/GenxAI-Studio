# lineage_tracker.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from datetime import datetime
import uuid


@dataclass(frozen=True)
class LineageNode:
    lineage_id: str
    parent_lineage_id: Optional[str]
    execution_id: str
    failure_reason: Optional[str]
    directive_delta: Dict
    timestamp: datetime


class LineageTracker:
    """
    Tracks execution lineage across halted runs.

    This is NOT a retry log.
    This is a causal history of cognitive succession.
    """

    def __init__(self):
        self._nodes: Dict[str, LineageNode] = {}

    def record(
        self,
        execution_id: str,
        parent_lineage_id: Optional[str],
        failure_reason: Optional[str],
        directive_delta: Dict,
    ) -> LineageNode:
        lineage_id = str(uuid.uuid4())

        node = LineageNode(
            lineage_id=lineage_id,
            parent_lineage_id=parent_lineage_id,
            execution_id=execution_id,
            failure_reason=failure_reason,
            directive_delta=directive_delta,
            timestamp=datetime.utcnow(),
        )

        self._nodes[lineage_id] = node
        return node

    def get(self, lineage_id: str) -> LineageNode | None:
        return self._nodes.get(lineage_id)

    def ancestry(self, lineage_id: str) -> List[LineageNode]:
        """
        Returns lineage ancestry, newest → oldest.
        """
        chain: List[LineageNode] = []
        current = self._nodes.get(lineage_id)

        while current:
            chain.append(current)
            current = (
                self._nodes.get(current.parent_lineage_id)
                if current.parent_lineage_id
                else None
            )

        return chain
