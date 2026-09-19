
with open("examples/manual_unrecoverable_loop.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    "except Exception as e:\n    print(f\"Execution interrupted: {e}\")",
    "except Exception as e:\n    print(f\"Execution interrupted: {e}\")\n\n# Wait for collector to create incident\ncollector._queue.join()\nimport time\ntime.sleep(0.5)\n"
)

with open("examples/manual_unrecoverable_loop.py", "w", encoding="utf-8") as f:
    f.write(content)

