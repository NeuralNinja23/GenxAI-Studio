# persistence/backends/sqlite/sqlite_failure_store.py

from __future__ import annotations
import sqlite3
from typing import Iterable, Optional
from datetime import datetime

from app.arbormind.persistence.interfaces.failure_store import (
    FailureStore,
    FailureEvent,
    FailureStats,
)


class SQLiteFailureStore(FailureStore):
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def record_event(self, event: FailureEvent) -> None:
        self._conn.execute(
            """
            INSERT INTO failure_events
            (id, fingerprint_id, domain, nature, recoverability,
             severity, context_hash, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.failure_id,
                event.fingerprint_id,
                event.domain,
                event.nature,
                event.recoverability,
                event.severity,
                event.context_hash,
                event.timestamp.isoformat(),
            ),
        )
        self._conn.commit()

    def stats_for(self, fingerprint_id: str) -> Optional[FailureStats]:
        cur = self._conn.execute(
            """
            SELECT COUNT(*), MAX(timestamp)
            FROM failure_events
            WHERE fingerprint_id = ?
            """,
            (fingerprint_id,),
        )
        row = cur.fetchone()
        if not row or row[0] == 0:
            return None

        return FailureStats(
            fingerprint_id=fingerprint_id,
            occurrence_count=row[0],
            last_seen=datetime.fromisoformat(row[1]),
        )

    def by_fingerprint(self, fingerprint_id: str) -> Iterable[FailureEvent]:
        cur = self._conn.execute(
            """
            SELECT id, fingerprint_id, domain, nature, recoverability,
                   severity, context_hash, timestamp
            FROM failure_events
            WHERE fingerprint_id = ?
            ORDER BY timestamp ASC
            """,
            (fingerprint_id,),
        )

        for row in cur:
            yield FailureEvent(
                failure_id=row[0],
                fingerprint_id=row[1],
                domain=row[2],
                nature=row[3],
                recoverability=row[4],
                severity=row[5],
                context_hash=row[6],
                timestamp=datetime.fromisoformat(row[7]),
            )
