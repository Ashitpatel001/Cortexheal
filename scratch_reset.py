
from cortexheal.storage.postgres import get_connection

with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS recovery_outcomes CASCADE")
        cur.execute("DROP TABLE IF EXISTS pattern_records CASCADE")
        conn.commit()

