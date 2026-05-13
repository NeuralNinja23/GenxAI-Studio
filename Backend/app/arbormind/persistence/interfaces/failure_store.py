# persistence/interfaces/failure_store.py

from __future__ import annotations
from typing import Iterable, Optional, Dict
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class FailureEvent:
    failure_id: str
    fingerprint_id: str
    domain: str
    nature: str
    recoverability: str
    severity: str
    context_hash: str
    timestamp: datetime


@dataclass(frozen=True)
class FailureStats:
    fingerprint_id: str
    occurrence_count: int
    last_seen: datetime


class FailureStore:
    """
    Persistence contract for failure memory.

    This store:
    - remembers WHAT failed
    - never remembers WHAT TO DO
    """

    def record_event(self, event: FailureEvent) -> None:
        raise NotImplementedError

    def stats_for(self, fingerprint_id: str) -> Optional[FailureStats]:
        raise NotImplementedError

    def by_fingerprint(self, fingerprint_id: str) -> Iterable[FailureEvent]:
        raise NotImplementedError
