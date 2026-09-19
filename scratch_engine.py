
with open("cortexheal/detection/engine.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("resumed[\"attempts_since_resume\"] < 3", "resumed[\"attempts_since_resume\"] < 20")

with open("cortexheal/detection/engine.py", "w", encoding="utf-8") as f:
    f.write(content)

