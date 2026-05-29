"""
inspect_db.py — Viewer for Sentinel failure memory databases
Run from backend/: python inspect_db.py
"""
import sqlite3
import json
import os

# Primary: Phase 6A failure memory
PRIMARY_DB   = os.path.normpath(os.path.join(os.path.dirname(__file__), "sentinel_memory.db"))
# Secondary: legacy memory.sqlite
SECONDARY_DB = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "memory.sqlite"))

DBS = [p for p in [PRIMARY_DB, SECONDARY_DB] if os.path.exists(p)]
if not DBS:
    print("No database files found.")
    raise SystemExit(1)


def hr(char="-", width=60):
    print(char * width)


for DB_PATH in DBS:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print()
    hr("=")
    print(f"  DATABASE: {DB_PATH}")
    hr("=")

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    print(f"  Tables found: {tables}\n")

    for table in tables:
        if table == "sqlite_sequence":
            continue

        hr()
        print(f"  TABLE: {table}")
        hr()

        cur.execute(f"PRAGMA table_info({table})")
        cols = [c[1] for c in cur.fetchall()]
        print(f"  Columns: {cols}")

        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"  Row count: {count}")

        if count == 0:
            print("  (empty)")
        else:
            cur.execute(f"SELECT * FROM {table} LIMIT 10")
            rows = cur.fetchall()
            print(f"\n  Rows (up to 10):")
            for i, row in enumerate(rows, 1):
                print(f"\n  [{i}]")
                for col, val in zip(cols, row):
                    if isinstance(val, str) and val.strip().startswith(("[", "{")):
                        try:
                            val = json.dumps(json.loads(val), indent=6)
                        except Exception:
                            pass
                    print(f"    {col}: {val}")

            if count > 10:
                print(f"\n  ... and {count - 10} more rows.")

        print()

    conn.close()
    hr("=")
    print("  Done.")
    hr("=")
    print()
