
import os

# 1. Update cortexheal/models/learning.py
with open("cortexheal/models/learning.py", "r", encoding="utf-8") as f:
    content = f.read()
if "org_id: str" not in content:
    content = content.replace("agent_id: str\n", "agent_id: str\n    org_id: str\n")
with open("cortexheal/models/learning.py", "w", encoding="utf-8") as f:
    f.write(content)

# 2. Update cortexheal/storage/postgres.py (Schema & Queries)
with open("cortexheal/storage/postgres.py", "r", encoding="utf-8") as f:
    p_content = f.read()

p_content = p_content.replace(
    "fingerprint VARCHAR(128) UNIQUE",
    "org_id VARCHAR(36) NOT NULL,\n                    fingerprint VARCHAR(128),\n                    UNIQUE(org_id, fingerprint)"
)

p_content = p_content.replace(
    "framework, agent_id, failure_type, fingerprint",
    "framework, agent_id, org_id, failure_type, fingerprint"
)
p_content = p_content.replace(
    "%(framework)s, %(agent_id)s, %(failure_type)s, %(fingerprint)s",
    "%(framework)s, %(agent_id)s, %(org_id)s, %(failure_type)s, %(fingerprint)s"
)
p_content = p_content.replace(
    "ON CONFLICT (fingerprint)",
    "ON CONFLICT (org_id, fingerprint)"
)

p_content = p_content.replace(
    "def get_pattern_by_fingerprint(fingerprint: str) -> Optional[Any]:",
    "def get_pattern_by_fingerprint(org_id: str, fingerprint: str) -> Optional[Any]:"
)
p_content = p_content.replace(
    "cur.execute(\"SELECT * FROM pattern_records WHERE fingerprint = %s\", (fingerprint,))",
    "cur.execute(\"SELECT * FROM pattern_records WHERE org_id = %s AND fingerprint = %s\", (org_id, fingerprint))"
)

old_patterns_query = """def get_patterns_by_org(org_id: str) -> List[Any]:
    from cortexheal.models.learning import PatternRecord
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(\"\"\"
                SELECT DISTINCT p.* 
                FROM pattern_records p
                JOIN runs r ON p.agent_id = r.agent_id
                WHERE r.org_id = %s
                ORDER BY p.updated_at DESC
            \"\"\", (org_id,))
            rows = cur.fetchall()"""

new_patterns_query = """def get_patterns_by_org(org_id: str) -> List[Any]:
    from cortexheal.models.learning import PatternRecord
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM pattern_records WHERE org_id = %s ORDER BY updated_at DESC", (org_id,))
            rows = cur.fetchall()"""

p_content = p_content.replace(old_patterns_query, new_patterns_query)

with open("cortexheal/storage/postgres.py", "w", encoding="utf-8") as f:
    f.write(p_content)

# 3. Update cortexheal/learning/pattern.py
with open("cortexheal/learning/pattern.py", "r", encoding="utf-8") as f:
    pat_content = f.read()

old_get_or_create = """    def get_or_create_pattern(self, incident: Incident, trigger_event: RuntimeEvent) -> PatternRecord:
        fingerprint = generate_fingerprint(incident, trigger_event)
        
        existing = get_pattern_by_fingerprint(fingerprint)"""

new_get_or_create = """    def get_or_create_pattern(self, incident: Incident, trigger_event: RuntimeEvent, org_id: str) -> PatternRecord:
        fingerprint = generate_fingerprint(incident, trigger_event)
        
        existing = get_pattern_by_fingerprint(org_id, fingerprint)"""

pat_content = pat_content.replace(old_get_or_create, new_get_or_create)

pat_content = pat_content.replace(
    "agent_id=trigger_event.agent_id,",
    "agent_id=trigger_event.agent_id,\n            org_id=org_id,"
)

with open("cortexheal/learning/pattern.py", "w", encoding="utf-8") as f:
    f.write(pat_content)

