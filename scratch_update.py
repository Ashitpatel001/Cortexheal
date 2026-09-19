
import re

with open("cortexheal/storage/postgres.py", "r", encoding="utf-8") as f:
    content = f.read()

new_func = """
def update_recovery_outcome_verification(incident_id: str, verification_result: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE recovery_outcomes SET verification_result = %s WHERE incident_id = %s",
                (verification_result, incident_id)
            )
            conn.commit()
"""

if "update_recovery_outcome_verification" not in content:
    with open("cortexheal/storage/postgres.py", "w", encoding="utf-8") as f:
        f.write(content + "\n" + new_func)

