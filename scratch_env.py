
with open(".env", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("5433", "5432")

with open(".env", "w", encoding="utf-8") as f:
    f.write(content)

