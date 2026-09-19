
with open("cortexheal/recovery/executor.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    "except Exception as e:\n            # Learning failure must never crash core execution\n            pass",
    "except Exception as e:\n            print(f\"Outcome save failed: {e}\")\n            pass"
)

with open("cortexheal/recovery/executor.py", "w", encoding="utf-8") as f:
    f.write(content)

