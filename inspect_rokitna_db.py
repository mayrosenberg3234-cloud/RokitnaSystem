import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "rokitna.db"
print("DB path:", DB_PATH)
print("Exists:", DB_PATH.exists())

with sqlite3.connect(DB_PATH) as conn:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [row[0] for row in cur.fetchall()]
    print("Tables:", tables)
    print()
    if 'Clients' in tables:
        print('Clients latest rows:')
        for row in cur.execute('SELECT clientId, name, phone, email, status, createdAt FROM Clients ORDER BY clientId DESC LIMIT 5'):
            print(row)
    else:
        print('No Clients table found.')
