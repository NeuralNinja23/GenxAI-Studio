# failure_memory.py
#
# ROLE: RECORD ONLY.
#
# This module stores WHAT failed and WHY.
# It does NOT decide anything.
# It does NOT block anything.
# It does NOT retry anything.
#
# Enforcement is StateGate's job. StateGate READS from here.

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from datetime import datetime
import uuid

from .state import FailureSeverity, FailureRecord


@dataclass
class FailureMemoryEntry:
    """Immutable record of a single failure observation."""
    entry_id: str
    fingerprint_id: str
    semantic_signature: str
    severity: FailureSeverity
    reason: str
    context: Dict
    first_seen: datetime
    last_seen: datetime
    count: int = 1


class FailureMemory:
    """
    Persistent failure cognition.

    Authority: RECORD ONLY.

    This module:
    - Stores Φ + metadata for every failure
    - Exposes the forbidden set for StateGate to read
    - Never decides, blocks, retries, or heals

    StateGate is the ONLY module that enforces.
    FailureMemory is the ONLY module that remembers.
    """

    def __init__(self) -> None:
        self._entries: Dict[str, FailureMemoryEntry] = {}
        self._forbidden_fingerprints: Set[str] = set()

    # ─────────────────────────────────────────────────────────
    # WRITE API (append-only)
    # ─────────────────────────────────────────────────────────

    def record(
        self,
        fingerprint_id: str,
        semantic_signature: str,
        severity: FailureSeverity,
        reason: str,
        context: Optional[Dict] = None,
    ) -> FailureMemoryEntry:
        """
        Record a failure. Append-only.

        This is the canonical way to remember a failure.
        After this call, the fingerprint is in the forbidden set forever.
        """
        now = datetime.utcnow()
        context = context or {}

        if fingerprint_id in self._entries:
            entry = self._entries[fingerprint_id]
            entry.count += 1
            entry.last_seen = now
            self._forbidden_fingerprints.add(fingerprint_id)
            return entry

        entry = FailureMemoryEntry(
            entry_id=str(uuid.uuid4()),
            fingerprint_id=fingerprint_id,
            semantic_signature=semantic_signature,
            severity=severity,
            reason=reason,
            context=context,
            first_seen=now,
            last_seen=now,
            count=1,
        )

        self._entries[fingerprint_id] = entry
        self._forbidden_fingerprints.add(fingerprint_id)
        return entry

    # ─────────────────────────────────────────────────────────
    # READ API (for StateGate)
    # ─────────────────────────────────────────────────────────

    @property
    def forbidden_fingerprints(self) -> Set[str]:
        """
        The set of all fingerprints that have ever failed.

        StateGate reads this. Nobody else writes enforcement logic.
        """
        return self._forbidden_fingerprints

    def is_forbidden(self, fingerprint_id: str) -> bool:
        """Check if a fingerprint is in the failure set."""
        return fingerprint_id in self._forbidden_fingerprints

    def get(self, fingerprint_id: str) -> Optional[FailureMemoryEntry]:
        """Get metadata for a failed fingerprint."""
        return self._entries.get(fingerprint_id)

    def all(self) -> List[FailureMemoryEntry]:
        """All failure entries."""
        return list(self._entries.values())

    def has_fatal(self) -> bool:
        """Check if any FATAL failure has been recorded."""
        return any(
            entry.severity == FailureSeverity.FATAL
            for entry in self._entries.values()
        )

    @property
    def count(self) -> int:
        return len(self._entries)
