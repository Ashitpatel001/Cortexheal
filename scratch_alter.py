
from cortexheal.storage.postgres import get_connection

with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE pattern_records ALTER COLUMN fingerprint TYPE VARCHAR(128)")
        conn.commit()

with open("cortexheal/storage/postgres.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("fingerprint VARCHAR(64) UNIQUE", "fingerprint VARCHAR(128) UNIQUE")

with open("cortexheal/storage/postgres.py", "w", encoding="utf-8") as f:
    f.write(content)

