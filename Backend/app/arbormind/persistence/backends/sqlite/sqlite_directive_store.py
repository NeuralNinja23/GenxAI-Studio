# persistence/backends/sqlite/sqlite_directive_store.py

from __future__ import annotations
import sqlite3
import json
from typing import Optional, List
from datetime import datetime

from app.arbormind.persistence.interfaces.directive_store import (
    DirectiveStore,
    CognitiveDirectiveSnapshot,
)


class SQLiteDirectiveStore(DirectiveStore):
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def save(self, snapshot: CognitiveDirectiveSnapshot) -> None:
        self._conn.execute(
            """
            INSERT INTO directive_snapshots
            (
                directive_id,
                execution_id,
                lineage_id,
                allowed_mutations,
                forbidden_mutations,
                attention_boosts,
                attention_penalties,
                derived_from_fingerprints,
                timestamp
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot.directive_id,
                snapshot.execution_id,
                snapshot.lineage_id,
                json.dumps(snapshot.allowed_mutations),
                json.dumps(snapshot.forbidden_mutations),
                json.dumps(snapshot.attention_boosts),
                json.dumps(snapshot.attention_penalties),
                json.dumps(snapshot.derived_from_fingerprints),
                snapshot.timestamp.isoformat(),
            ),
        )
        self._conn.commit()

    def load_by_execution(
        self, execution_id: str
    ) -> Optional[CognitiveDirectiveSnapshot]:
        cur = self._conn.execute(
            """
            SELECT
                directive_id,
                execution_id,
                lineage_id,
                allowed_mutations,
                forbidden_mutations,
                attention_boosts,
                attention_penalties,
                derived_from_fingerprints,
                timestamp
            FROM directive_snapshots
            WHERE execution_id = ?
            LIMIT 1
            """,
            (execution_id,),
        )

        row = cur.fetchone()
        if not row:
            return None

        return CognitiveDirectiveSnapshot(
            directive_id=row[0],
            execution_id=row[1],
            lineage_id=row[2],
            allowed_mutations=json.loads(row[3]),
            forbidden_mutations=json.loads(row[4]),
            attention_boosts=json.loads(row[5]),
            attention_penalties=json.loads(row[6]),
            derived_from_fingerprints=json.loads(row[7]),
            timestamp=datetime.fromisoformat(row[8]),
        )

    def history_by_lineage(
        self, lineage_id: str
    ) -> List[CognitiveDirectiveSnapshot]:
        cur = self._conn.execute(
            """
            SELECT
                directive_id,
                execution_id,
                lineage_id,
                allowed_mutations,
                forbidden_mutations,
                attention_boosts,
                attention_penalties,
                derived_from_fingerprints,
                timestamp
            FROM directive_snapshots
            WHERE lineage_id = ?
            ORDER BY timestamp ASC
            """,
            (lineage_id,),
        )

        snapshots: List[CognitiveDirectiveSnapshot] = []

        for row in cur:
            snapshots.append(
                CognitiveDirectiveSnapshot(
                    directive_id=row[0],
                    execution_id=row[1],
                    lineage_id=row[2],
                    allowed_mutations=json.loads(row[3]),
                    forbidden_mutations=json.loads(row[4]),
                    attention_boosts=json.loads(row[5]),
                    attention_penalties=json.loads(row[6]),
                    derived_from_fingerprints=json.loads(row[7]),
                    timestamp=datetime.fromisoformat(row[8]),
                )
            )

        return snapshots
