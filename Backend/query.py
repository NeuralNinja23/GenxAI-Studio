import sqlite3
import pprint

c = sqlite3.connect('data/memory.sqlite')
tables = c.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
print("Tables:", tables)

for table in tables:
    name = table[0]
    print(f"\n--- {name} ---")
    rows = c.execute(f"SELECT * FROM {name} LIMIT 5;").fetchall()
    for row in rows:
        print(row)
