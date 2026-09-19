
import re

with open("cortexheal/storage/postgres.py", "r", encoding="utf-8") as f:
    content = f.read()

new_func = """
def get_patterns_by_org(org_id: str) -> List[Any]:
    from cortexheal.models.learning import PatternRecord
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(\"""
                SELECT DISTINCT p.* 
                FROM pattern_records p
                JOIN recovery_outcomes o ON p.pattern_id = o.pattern_id
                JOIN runs r ON o.run_id = r.run_id
                WHERE r.org_id = %s
                ORDER BY p.updated_at DESC
            \""", (org_id,))
            rows = cur.fetchall()
            
    patterns = []
    for row in rows:
        row["created_at"] = row["created_at"].isoformat()
        row["updated_at"] = row["updated_at"].isoformat()
        patterns.append(PatternRecord(**row))
    return patterns
"""

if "get_patterns_by_org" not in content:
    with open("cortexheal/storage/postgres.py", "w", encoding="utf-8") as f:
        f.write(content + "\n" + new_func)

