
with open("cortexheal/models/run.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    "agent_id: str",
    "agent_id: str\n    org_id: str = \"default_org\""
)

with open("cortexheal/models/run.py", "w", encoding="utf-8") as f:
    f.write(content)

