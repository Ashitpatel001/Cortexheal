
with open("test_isolation.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("from cortexheal.models.users import User", "from cortexheal.server.api import User")

with open("test_isolation.py", "w", encoding="utf-8") as f:
    f.write(content)

