# persistence/backends/sqlite/sqlite_lineage_store.py

from __future__ import annotations
import sqlite3
import json
from typing import Optional, Iterable
from datetime import datetime

from app.arbormind.persistence.interfaces.lineage_store import (
    LineageStore,
    LineageNodeRecord,
)


class SQLiteLineageStore(LineageStore):
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def add_node(self, node: LineageNodeRecord) -> None:
        self._conn.execute(
            """
            INSERT INTO lineage_nodes
            (lineage_id, parent_lineage_id, execution_id,
             failure_fingerprint_id, directive_delta, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                node.lineage_id,
                node.parent_lineage_id,
                node.execution_id,
                node.failure_fingerprint_id,
                json.dumps(node.directive_delta),
                node.timestamp.isoformat(),
            ),
        )
        self._conn.commit()

    def get(self, lineage_id: str) -> Optional[LineageNodeRecord]:
        cur = self._conn.execute(
            """
            SELECT lineage_id, parent_lineage_id, execution_id,
                   failure_fingerprint_id, directive_delta, timestamp
            FROM lineage_nodes
            WHERE lineage_id = ?
            """,
            (lineage_id,),
        )
        row = cur.fetchone()
        if not row:
            return None

        return LineageNodeRecord(
            lineage_id=row[0],
            parent_lineage_id=row[1],
            execution_id=row[2],
            failure_fingerprint_id=row[3],
            directive_delta=json.loads(row[4]),
            timestamp=datetime.fromisoformat(row[5]),
        )

    def ancestry(self, lineage_id: str) -> Iterable[LineageNodeRecord]:
        current = self.get(lineage_id)
        while current:
            yield current
            if not current.parent_lineage_id:
                break
            current = self.get(current.parent_lineage_id)
