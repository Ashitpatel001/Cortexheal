
with open(".env", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("5432", "5434")
content = content.replace("5433", "5434")

with open(".env", "w", encoding="utf-8") as f:
    f.write(content)

