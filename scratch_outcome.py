
from cortexheal.storage.postgres import get_connection
with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT verification_result, action_type FROM recovery_outcomes ORDER BY timestamp DESC LIMIT 5")
        for r in cur.fetchall():
            print(r)

