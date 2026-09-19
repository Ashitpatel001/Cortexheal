
with open("cortexheal/storage/postgres.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    """JOIN recovery_outcomes o ON p.pattern_id = o.pattern_id
                JOIN runs r ON o.run_id = r.run_id""",
    """JOIN runs r ON p.agent_id = r.agent_id"""
)

with open("cortexheal/storage/postgres.py", "w", encoding="utf-8") as f:
    f.write(content)

