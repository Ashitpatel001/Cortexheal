
with open("test_isolation.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("status=\"success\"", "status=\"success\", idempotency_key=str(uuid.uuid4())")

with open("test_isolation.py", "w", encoding="utf-8") as f:
    f.write(content)

